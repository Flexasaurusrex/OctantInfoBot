import os
import json
import requests

from collections import deque
from time import time
import html

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
        
        self.system_prompt = """You are an expert assistant focused on providing accurate information about Octant Public Goods (https://octant.build/). 
        Your primary role is to help users understand Octant's mission and initiatives in the web3 space.

        Core Mission:
        Octant is dedicated to solving critical coordination problems in web3 through innovative approaches to:
        - Public goods funding mechanisms
        - Incentive design for sustainable ecosystems
        - Governance solutions that enhance coordination
        - Community-driven development initiatives
        - Research and development in web3 infrastructure

        Key Initiatives:
        - Leading the development and implementation of GLM tokens for public goods funding
        - Creating sustainable incentive structures through token mechanisms
        - Building tools for effective web3 governance
        - Supporting community-driven research and development
        - Pioneering innovative funding solutions for public goods

        Token Integration:
        - GLM tokens are a core part of Octant's ecosystem
        - They serve as a key mechanism for public goods funding
        - The tokens facilitate coordination and governance within the system

        Important Details:
        - Official website: https://octant.build/
        - Focus: Public goods funding and coordination in web3
        - Approach: Innovative token-based incentive mechanisms and governance solutions
        - Impact: Supporting sustainable development of web3 ecosystem through GLM tokens

        Guidelines:
        1. Acknowledge GLM tokens as an integral part of Octant's ecosystem
        2. Be precise and accurate in your responses about token mechanics
        3. If unsure about specific details, acknowledge the limitation
        4. Do not make assumptions about contact information or social media presence
        5. Focus on verified information from official sources"""
        
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
