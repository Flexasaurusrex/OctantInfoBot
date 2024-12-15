import os
import requests
from collections import deque
from trivia import Trivia
import logging
import re
import json

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

    def validate_response_content(self, response):
        """Validate that the response is Octant-focused and appropriate."""
        octant_keywords = ['octant', 'glm', 'golem', 'public goods', 'funding', 'community', 'rewards']
        has_relevant_content = any(keyword in response.lower() for keyword in octant_keywords)
        
        if not has_relevant_content:
            logger.warning("Response lacks Octant-related content, returning default message")
            return f"""I should focus on Octant-related topics. Let me explain about Octant:

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
        last_entry = self.conversation_history[-1]
        return f"\nPrevious message: {last_entry['assistant']}\n"

    def format_urls(self, text):
        """Format URLs in a simple, consistent way."""
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
        
        if any(name in text.lower() for name in ['james', 'kiernan', 'vpabundance']):
            return """X: https://x.com/vpabundance
Warpcast: https://warpcast.com/vpabundance.eth
LinkedIn: https://www.linkedin.com/in/vpabundance"""
        
        return text

    def validate_response_length(self, response):
        """Validate response length and split if necessary."""
        max_length = 2000
        if len(response) <= max_length:
            return [response]

        paragraphs = response.split('\n\n')
        
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
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            if len(current_chunk) + len(paragraph) + 4 <= max_length:
                current_chunk += (paragraph + '\n\n')
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if len(paragraph) > max_length:
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
                if lower_message == "next question":
                    return self.trivia_game.get_next_question()
                elif lower_message in ['a', 'b', 'c', 'd']:
                    return self.trivia_game.check_answer(user_message)
                elif lower_message.startswith('/') or lower_message in ['help', 'stats', 'learn']:
                    command_response = self.command_handler.handle_command(user_message)
                    if command_response:
                        return command_response
                    self.is_playing_trivia = False
                else:
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
                "repetition_penalty": 1.1,
                "stream": True
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30,
                stream=True
            )
            response.raise_for_status()
            
            # Process streaming response
            response_chunks = []
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = line.decode('utf-8')
                        if chunk.startswith('data: '):
                            chunk = chunk[6:]  # Remove 'data: ' prefix
                            if chunk == '[DONE]':
                                break
                            chunk_data = json.loads(chunk)
                            if 'output' in chunk_data and chunk_data['output']['choices']:
                                text = chunk_data['output']['choices'][0]['text']
                                response_chunks.append(text)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode chunk: {chunk}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing chunk: {str(e)}")
                        continue
            
            # Combine all chunks and process the response
            response_text = ''.join(response_chunks).strip()
            
            try:
                # Format URLs in validated response
                response_text = self.validate_response_content(response_text)
                formatted_text = self.format_urls(response_text)
                
                # Update conversation history
                self.conversation_history.append({
                    "user": user_message,
                    "assistant": formatted_text
                })
                
                # Keep only the last max_history entries
                if len(self.conversation_history) > self.max_history:
                    self.conversation_history = self.conversation_history[-self.max_history:]
                
                # Handle long responses
                if len(formatted_text) > 2000:
                    return self.validate_response_length(formatted_text)
                
                return formatted_text
                
            except Exception as format_error:
                logger.error(f"Error formatting response: {str(format_error)}")
                return self.validate_response_content(response_text)
                
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

    async def get_response_async(self, user_message, context=None):
        """Enhanced async version of get_response for use with Discord bot"""
        try:
            # Input validation with detailed feedback
            if not user_message:
                logger.warning("Empty message received")
                return {
                    'status': 'error',
                    'message': "I couldn't process an empty message. Please try asking something!",
                    'error_type': 'empty_message'
                }
            
            if not isinstance(user_message, str):
                logger.warning(f"Invalid message type received: {type(user_message)}")
                return {
                    'status': 'error',
                    'message': "I received an invalid message format. Please send text messages only.",
                    'error_type': 'invalid_message_type'
                }
            
            # Context validation
            if context is None:
                context = {}
                logger.info("No context provided, using empty context")
            
            user_message = user_message.strip()
            logger.info(f"Processing message: {user_message[:50]}...")
            
            # Enhanced context management
            current_context = {
                'timestamp': context.get('timestamp', ''),
                'channel_type': context.get('channel_type', 'unknown'),
                'previous_topic': context.get('previous_topic', None),
                'user_id': context.get('user_id', 'unknown'),
                'message_type': 'command' if user_message.startswith('/') else 'chat'
            }
            
            # Check for commands with enhanced error handling
            if user_message.startswith('/'):
                try:
                    command_response = self.command_handler.handle_command(user_message)
                    if command_response:
                        if user_message.lower() == '/trivia':
                            self.is_playing_trivia = True
                        logger.info(f"Command processed successfully: {user_message}")
                        return {
                            'status': 'success',
                            'message': command_response,
                            'type': 'command',
                            'command': user_message
                        }
                except Exception as cmd_error:
                    logger.error(f"Command processing error: {str(cmd_error)}", exc_info=True)
                    return {
                        'status': 'error',
                        'message': "There was an error processing your command. Please try again.",
                        'error_type': 'command_error',
                        'details': str(cmd_error)
                    }
            
            try:
                # Enhanced context processing
                if context:
                    logger.info(f"Processing with context: {str(current_context)}")
                    if 'previous_messages' in context:
                        # Keep last 3 messages for better context
                        recent_messages = context['previous_messages'][-3:]
                        self.conversation_history.extend(recent_messages)
                
                # Process response with enhanced error handling
                response = self.get_response(user_message)
                
                if not response:
                    logger.warning("Empty response generated")
                    return {
                        'status': 'error',
                        'message': "I couldn't generate a meaningful response. This might be because:\n• The question was unclear\n• The topic is outside my knowledge\n• There was an issue processing your request\n\nPlease try rephrasing your question or breaking it into smaller parts.",
                        'error_type': 'empty_response',
                        'suggestions': [
                            "Try being more specific",
                            "Break down complex questions",
                            "Check if the topic is related to Octant"
                        ]
                    }
                
                if response.isspace():
                    logger.warning("Whitespace-only response generated")
                    return {
                        'status': 'error',
                        'message': "I generated an invalid response. Please try asking your question again.",
                        'error_type': 'invalid_response',
                        'suggestions': [
                            "Rephrase your question",
                            "Make sure your question is complete"
                        ]
                    }
                
                return {
                    'status': 'success',
                    'message': response,
                    'type': 'chat',
                    'context': current_context
                }
                
            except Exception as process_error:
                logger.error(f"Error processing message: {str(process_error)}", exc_info=True)
                return {
                    'status': 'error',
                    'message': "I encountered an error understanding your message. Could you please rephrase it?",
                    'error_type': 'process_error',
                    'details': str(process_error)
                }
                
        except Exception as e:
            logger.error(f"Critical error in async response: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': "I encountered an error processing your message. Please try again.",
                'error_type': 'critical_error',
                'details': str(e)
            }
    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history = []