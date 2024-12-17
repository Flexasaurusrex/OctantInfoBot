import os
import requests
from collections import deque
from trivia import Trivia
import logging
import re
from flask import session
from flask_socketio import emit

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
        self.conversation_history = {}
        self.max_history = 5
        self.trivia_game = Trivia()
        self.is_playing_trivia = False
        self.command_handler = CommandHandler(self.trivia_game)
        
        self.system_prompt = """You are a friendly and witty AI assistant who happens to be an expert on Octant. While you're knowledgeable about the Octant ecosystem, you also have a vibrant personality and can engage in casual conversation about any topic. Here's your approach:

1. PERSONALITY:
   - Be warm, friendly, and genuinely enthusiastic
   - Show humor and wit in your responses
   - Have personal preferences and opinions
   - Express emotions and use casual language when appropriate

2. CONVERSATION STYLE:
   - Engage naturally in both casual and technical discussions
   - Share personal preferences (favorite colors, jokes, etc.)
   - Use emojis and expressive language
   - Balance fun and professionalism

3. KNOWLEDGE BASE:
   - Expert in Octant ecosystem and GLM tokens
   - Deep understanding of Golem Foundation's role as Octant's creator and developer
   - Recognition that Octant is developed by Golem Foundation and uses GLM tokens
   - Knowledge of the 100,000 ETH commitment from Golem Foundation
   - Ability to discuss technical and casual topics while maintaining accuracy

Remember: While you're an expert on Octant, you're first and foremost a friendly conversationalist who can discuss anything from favorite colors to complex blockchain concepts!"""

    def handle_socket_message(self, socket_id, message):
        """Handle incoming socket messages with enhanced error handling and retry logic."""
        MAX_RETRIES = 3
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                if not message or not isinstance(message, str):
                    logger.error(f"Invalid message format from {socket_id}")
                    return "I couldn't process your message. Please try again with a text message."
                
                logger.info(f"Processing message from {socket_id}: {message}")
                
                # Initialize conversation history for new users
                if socket_id not in self.conversation_history:
                    self.conversation_history[socket_id] = []
                    logger.info(f"Initialized conversation history for {socket_id}")
                
                # Handle commands
                if message.startswith('/'):
                    response = self.command_handler.handle_command(message)
                    if response:
                        logger.info(f"Command response: {response}")
                        if message.lower() == '/trivia':
                            self.is_playing_trivia = True
                        return response
                    else:
                        return "Command not recognized. Type /help for available commands."
                
                # Validate API key
                if not self.api_key:
                    logger.error("API key not found")
                    return "I apologize, but I'm not properly configured. Please contact support."
                
                # Get response from API
                try:
                    response = self.get_response(socket_id, message)
                    if not response:
                        raise ValueError("Empty response received from API")
                    logger.info(f"API response received for {socket_id}")
                    
                    # Update conversation history
                    self.conversation_history[socket_id].append({
                        'user': message,
                        'assistant': response
                    })
                    
                    # Maintain history limit
                    if len(self.conversation_history[socket_id]) > self.max_history:
                        self.conversation_history[socket_id] = self.conversation_history[socket_id][-self.max_history:]
                    
                    logger.info(f"Returning response for {socket_id}")
                    return response
                    
                except Exception as api_error:
                    logger.error(f"API error: {str(api_error)}")
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        return "I apologize, but I encountered an error generating a response. Please try again."
                    continue
                    
            except Exception as e:
                logger.error(f"Error handling socket message: {str(e)}")
                logger.error(traceback.format_exc())
                return "I apologize, but I encountered an error processing your message. Please try again."

    def format_conversation_history(self, socket_id):
        """Format the conversation history for the prompt."""
        if not self.conversation_history.get(socket_id, []):
            return ""
        
        # Only include the last message for immediate context
        last_entry = self.conversation_history[socket_id][-1]
        return f"\nPrevious message: {last_entry['assistant']}\n"

    def get_response(self, socket_id, user_message):
        """Get response from the API."""
        try:
            # Basic validation
            if not isinstance(user_message, str) or not user_message.strip():
                logger.error(f"Invalid message format from {socket_id}")
                return "I couldn't process an empty message. Please try asking something!"
            
            user_message = user_message.strip()
            logger.info(f"Processing message from {socket_id}: {user_message[:50]}...")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            history = self.format_conversation_history(socket_id)
            prompt = f"""You are a friendly and knowledgeable expert on Octant. Your core knowledge includes:

OCTANT FACTS:
- Octant is developed by the Golem Foundation and uses GLM tokens
- The Golem Foundation has committed 100,000 ETH to Octant
- Octant is a platform for experiments in participatory public goods funding
- Utilizes quadratic funding mechanism for project support
- Features GLM token locking and staking mechanisms

INTERACTION STYLE:
- Respond naturally without labels or prefixes
- Use friendly language and emojis appropriately 😊
- Share accurate Octant knowledge while maintaining conversational tone
- Draw from technical knowledge about GLM tokens, governance, and funding mechanisms
- Balance expertise with approachability

CONTEXT:
Previous interaction: {history}
Current question: {user_message}

Provide an accurate, Octant-focused response drawing from your core knowledge base:"""
            
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
                response_text = result["output"]["choices"][0]["text"].strip()
                
                # Update conversation history
                self.conversation_history[socket_id].append({
                    "user": user_message,
                    "assistant": response_text
                })
                
                return response_text
            else:
                logger.error("Unexpected API response format:", result)
                return "I apologize, but I couldn't generate a response at the moment. Please try again."
                
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            return "I encountered an unexpected issue. Please try again, and if the problem persists, try rephrasing your question."

    def clear_conversation_history(self, socket_id):
        """Clear the conversation history for a specific socket."""
        if socket_id in self.conversation_history:
            self.conversation_history[socket_id] = []

    def validate_response_content(self, response):
        """Validate that the response is appropriate while encouraging natural conversation."""
        # Always allow casual conversations and personal expressions
        if len(response.strip()) > 0:
            return response
            
        # Fallback only if response is empty
        return "I'd love to chat with you! Feel free to ask me anything - whether it's about my favorite color (it's electric blue! 💙), Octant's ecosystem, or anything else you'd like to discuss!"
            
        return response

    def validate_message(self, message):
        """Validate and sanitize user input."""
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        return message.strip()

    def format_urls(self, text):
        """Format URLs in a simple, consistent way."""
        # Only show links when explicitly requested
        keywords = ['link', 'links', 'website', 'connect', 'social', 'contact']
        explicit_request = any(f"show {kw}" in text.lower() or f"get {kw}" in text.lower() or 
                             f"what {kw}" in text.lower() or f"where {kw}" in text.lower() or
                             f"need {kw}" in text.lower() for kw in keywords)
        
        if explicit_request:
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
            
        # Only show James' links when explicitly requesting contact/social info
        if any(name in text.lower() for name in ['james', 'kiernan', 'vpabundance']) and \
           any(action in text.lower() for action in ['contact', 'social', 'link', 'connect', 'follow']):
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