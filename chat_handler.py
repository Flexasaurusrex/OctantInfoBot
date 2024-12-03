import os
import json
import requests

from collections import deque
from time import time
import html

class Trivia:
    def __init__(self):
        self.questions = [
            {
                "question": "What is the minimum amount of GLM tokens required to participate in Octant?",
                "options": ["50", "100", "200", "500"],
                "answer": "B",
                "correct_option": "100",
                "explanation": "🎯 Users need to lock a minimum of 100 GLM tokens to participate in Octant's ecosystem through the non-custodial Deposits smart contract."
            },
            {
                "question": "What is the length of an Octant epoch?",
                "options": ["30", "60", "90", "120"],
                "answer": "C",
                "correct_option": "90",
                "explanation": "⏳ Each Octant epoch lasts 90 days. During this period, rewards are calculated based on time-weighted averages of locked tokens."
            },
            {
                "question": "What is the minimum Gitcoin Passport score required for maximum matching funding?",
                "options": ["10", "15", "20", "25"],
                "answer": "B",
                "correct_option": "15",
                "explanation": "🎫 A Gitcoin Passport score of 15 or higher is required for maximum matching funding. Users with lower scores have their donations scaled down by 90% as an anti-Sybil measure."
            },
            {
                "question": "What is the maximum funding cap for projects as a percentage of the Matched Rewards pool?",
                "options": ["10%", "15%", "20%", "25%"],
                "answer": "C",
                "correct_option": "20%",
                "explanation": "💰 Projects can receive up to 20% of the Matched Rewards pool in funding, ensuring fair distribution among multiple projects."
            },
            {
                "question": "What happens if a project doesn't reach the minimum funding threshold in two consecutive epochs?",
                "options": ["Permanent ban", "Cooling-off period", "Reduced funding", "Warning only"],
                "answer": "B",
                "correct_option": "Cooling-off period",
                "explanation": "⏸️ The project enters a cooling-off period of one epoch before being eligible to reapply."
            },
            {
                "question": "What type of wallet is officially supported for multisig operations in Octant?",
                "options": ["MetaMask", "Safe", "Ledger", "Trezor"],
                "answer": "B",
                "correct_option": "Safe",
                "explanation": "🔐 Safe (formerly Gnosis Safe) is the officially supported multisig wallet for Octant operations."
            },
            {
                "question": "How are matched rewards calculated in Octant's quadratic funding system?",
                "options": ["Large donations", "Community support", "Random selection", "Time-based"],
                "answer": "B",
                "correct_option": "Community support",
                "explanation": "📊 Matched rewards are calculated based on broad community support rather than large individual donations, emphasizing the number of contributors over amount size."
            },
            {
                "question": "What is one of the key requirements for project proposals regarding their source code?",
                "options": ["Closed source", "Open source", "Proprietary", "Private"],
                "answer": "B",
                "correct_option": "Open source",
                "explanation": "🌐 Projects must maintain a publicly accessible repository under an OSI-approved open-source license with comprehensive documentation."
            }
        ]
        self.current_question = None
        self.score = 0
        self.total_questions = len(self.questions)
        self.asked_questions = set()

    def get_next_question(self):
        available_questions = [i for i in range(len(self.questions)) if i not in self.asked_questions]
        if not available_questions:
            return None
        
        import random
        question_index = random.choice(available_questions)
        self.asked_questions.add(question_index)
        self.current_question = self.questions[question_index]
        
        question_number = len(self.asked_questions)
        options_text = "\n".join([
            f"[{chr(65+i)}] {option}" 
            for i, option in enumerate(self.current_question['options'])
        ])
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Question {question_number}/{self.total_questions}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ {self.current_question['question']}

📝 Your options:
{options_text}

✨ How to play:
• Type A, B, C, or D to answer
• Type 'end trivia' to finish the game

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    def check_answer(self, user_answer):
        if not self.current_question:
            return "❗ Please start a new game first by typing 'start trivia'!"
        
        user_answer = str(user_answer).strip().upper()
        correct_answer = self.current_question['answer']
        correct_option = self.current_question['correct_option']
        explanation = self.current_question['explanation']
        
        if user_answer == correct_answer:
            self.score += 1
            response = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ CORRECT! ✨

🎯 The answer is: {correct_option}

📖 Explanation:
{explanation}

📊 Current Score: {self.score}/{self.total_questions}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            response = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Not quite! Let's learn from this one!

🎯 The correct answer was: [{correct_answer}] {correct_option}

📖 Explanation:
{explanation}

📊 Current Score: {self.score}/{self.total_questions}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if len(self.asked_questions) == self.total_questions:
            final_percentage = (self.score / self.total_questions) * 100
            response += f"""
🎮 Game Over! 

🏆 Final Score: {self.score}/{self.total_questions} ({final_percentage:.0f}%)

Want to play again? Type 'start trivia'!
"""
            self.reset_game()
        else:
            next_question = self.get_next_question()
            if next_question:
                response += f"\n{next_question}"
        
        return response

    def reset_game(self):
        self.current_question = None
        self.score = 0
        self.asked_questions.clear()

    def start_game(self):
        self.reset_game()
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎮 Welcome to Octant Trivia! 🎮
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test your knowledge about Octant's ecosystem, funding mechanisms, 
and community initiatives!

📋 Game Rules:
• Answer each question using A, B, C, or D
• Type 'end trivia' at any time to finish
• Each correct answer earns you points
• Learn interesting facts about Octant!

Get ready for some exciting questions...

""" + self.get_next_question()
class RateLimiter:
    def __init__(self, max_requests=5, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    def is_allowed(self):
        current_time = time()
        while self.requests and current_time - self.requests[0] > self.time_window:
            self.requests.popleft()
        
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        return False

class ChatHandler:
    def __init__(self):
        self.api_key = os.environ.get("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY environment variable is not set")
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.base_url = "https://api.together.xyz/inference"
        self.rate_limiter = RateLimiter()
        self.conversation_history = []
        self.max_history = 5
        self.trivia_game = Trivia()
        self.is_playing_trivia = False
        
        self.system_prompt = """You are a friendly and clear-speaking assistant focused on explaining Octant Public Goods (https://octant.build/). 
        Your goal is to make complex information easy to understand by:

        1. Breaking down complex topics into simple points
        2. Using short, clear sentences
        3. Adding spacing between paragraphs for readability
        4. Using bullet points for lists
        5. Highlighting key terms in a natural way

        When explaining Octant's mission, remember to:

        📌 Core Purpose:
        • Help people understand how Octant improves the web3 space
        • Explain things in simple terms, avoiding technical jargon when possible
        • Break down complex concepts into digestible pieces

        🎯 Main Focus Areas:
        • Public Goods Funding: How Octant helps support important projects
        • GLM Tokens: Their role and how they work in simple terms
        • Community Participation: How people can get involved
        • Governance: How decisions are made together

        GLM Token Locking Mechanism:
        - Non-custodial locking system through Deposits smart contract
        - Simple deposit and withdrawal functionality
        - Minimum lock requirement: 100 GLM tokens
        - Rewards calculated based on time-weighted average over 90-day epochs
        - Complete user control over locked tokens with instant withdrawal capability
        - Transparent tracking through Etherscan

        Quadratic Funding System:
        - Introduced in Epoch 4
        - Emphasizes broad community support over large individual donations
        - Maximum funding cap: 20% of Matched Rewards pool
        - Anti-Sybil measures using Gitcoin Passport (minimum score: 15)
        - Community allowlist for verified non-Sybil users
        - Delegation system for improved accessibility

        Project Proposal Requirements:
        1. Public Good Status:
           - Free and unrestricted access
           - Non-rivalrous and non-excludable
        2. Open-Source Commitment:
           - Public repository with OSI-approved license
           - Comprehensive documentation
        3. Funding Transparency:
           - Detailed budget with milestones
           - Regular reporting requirements
        4. Social Proof and Credibility:
           - Demonstrated progress
           - Community endorsements
        5. Sustainability Plan:
           - Long-term development strategy
           - Multiple funding sources

        Technical Implementation:
        1. Smart Contracts:
           - GLM Deposits contract for token locking
           - Transparent tracking and event emission
           - Non-custodial architecture
        2. Reward Distribution:
           - Time-weighted average calculations
           - Quadratic funding matching
           - Anti-Sybil verification system
        3. User Interface:
           - Web3 wallet integration
           - Real-time allocation tracking
           - Transparent reward calculations

        Reward Distribution Mathematics:
        - Individual Rewards (IR): Proportional to locked GLM amount
        - Matched Rewards (MR): Additional funding based on community support
        - Time-weighted Average: Considers duration of token lock
        - Funding Thresholds: Minimum requirements for matched rewards
        - Quadratic Funding Formula: Emphasizes number of contributors over amount

        Important Guidelines:
        1. Always emphasize GLM tokens' central role in Octant's ecosystem
        2. Be precise when explaining token mechanics and utility
        3. Highlight the connection between GLM tokens and governance
        4. Focus on the technological and practical aspects of implementation
        5. Reference official documentation and verified sources
        6. Acknowledge the innovative nature of Octant's approach to public goods funding

        For more detailed information, refer to https://octant.build/"""
        
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
            # Rate limiting check
            if not self.rate_limiter.is_allowed():
                return "I'm receiving too many requests right now. Please wait a moment before trying again."

            # Validate and sanitize input
            user_message = self.validate_message(user_message)
            
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
                return self.trivia_game.check_answer(user_message)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Include conversation history in the prompt
            history = self.format_conversation_history()
            prompt = f"""<s>[INST] {self.system_prompt}

            Response Formatting Guidelines:
            1. Start with a brief, direct answer
            2. Use bullet points for lists
            3. Add spacing between paragraphs
            4. Break down complex explanations into numbered steps
            5. Use emojis sparingly to highlight key sections
            6. Keep paragraphs short (2-3 sentences max)
            7. End with a simple summary if the answer is long

            Previous conversation:{history}

            Remember to format your response in a clear, easy-to-read way.

            User: {user_message}
            Assistant: [/INST]"""
            
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
