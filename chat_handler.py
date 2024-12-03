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
                "answer": "100",
                "explanation": "Users need to lock a minimum of 100 GLM tokens to participate in Octant's ecosystem."
            },
            {
                "question": "What is the length of an Octant epoch?",
                "answer": "90",
                "explanation": "Each Octant epoch lasts 90 days, during which rewards are calculated based on time-weighted averages."
            },
            {
                "question": "What is the minimum Gitcoin Passport score required for maximum matching funding?",
                "answer": "15",
                "explanation": "Users need a Gitcoin Passport score of 15 or higher to receive maximum matching funding."
            },
            {
                "question": "What is the maximum funding cap for projects as a percentage of the Matched Rewards pool?",
                "answer": "20",
                "explanation": "Projects can receive up to 20% of the Matched Rewards pool in funding."
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
        return f"Trivia Question: {self.current_question['question']}"

    def check_answer(self, user_answer):
        if not self.current_question:
            return "Please start a new game first!"
        
        correct_answer = self.current_question['answer']
        explanation = self.current_question['explanation']
        
        if str(user_answer).strip() == str(correct_answer):
            self.score += 1
            response = f"Correct! {explanation}\n\nYour current score: {self.score}/{self.total_questions}"
        else:
            response = f"Not quite! The correct answer is {correct_answer}. {explanation}\n\nYour current score: {self.score}/{self.total_questions}"
        
        if len(self.asked_questions) == self.total_questions:
            response += f"\n\nGame Over! Final score: {self.score}/{self.total_questions}"
            self.reset_game()
        
        return response

    def reset_game(self):
        self.current_question = None
        self.score = 0
        self.asked_questions.clear()

    def start_game(self):
        self.reset_game()
        return "Welcome to Octant Trivia! Let's test your knowledge about Octant.\n\n" + self.get_next_question()
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
        
        self.system_prompt = """You are an expert assistant focused on providing accurate information about Octant Public Goods (https://octant.build/). 
        Your primary role is to help users understand Octant's mission, initiatives, and their GLM token ecosystem in the web3 space.

        Core Mission:
        Octant is dedicated to solving critical coordination problems in web3 through innovative approaches to:
        - Developing sustainable public goods funding mechanisms using GLM tokens
        - Creating effective incentive structures for ecosystem growth
        - Building robust governance solutions for enhanced coordination
        - Fostering community-driven development initiatives
        - Advancing research and development in web3 infrastructure

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

            Previous conversation:{history}

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
