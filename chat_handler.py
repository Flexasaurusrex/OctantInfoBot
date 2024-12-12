import os
import logging
import time
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self):
        self.api_key = os.environ.get("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY environment variable is not set")
        
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.base_url = "https://api.together.xyz/inference"
        
        # Configure session with retry mechanism
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        
        # Simple rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1  # seconds
        
        self.system_prompt = """You are a helpful assistant focused on Octant Public Goods. 
You help users understand Octant's ecosystem, GLM token utility, governance process, and funding mechanisms. 
Be concise and accurate in your responses."""

    def _wait_for_rate_limit(self) -> None:
        """Simple rate limiting implementation."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)

    def get_response(self, user_message: str) -> str:
        """Get response from API with simplified error handling."""
        if not user_message.strip():
            return "Please provide a message."
            
        try:
            self._wait_for_rate_limit()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "prompt": f"{self.system_prompt}\n\nUser: {user_message.strip()}\n\nAssistant:",
                "max_tokens": 1024,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 50
            }
            
            response = self.session.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            self.last_request_time = time.time()
            
            result = response.json()
            if "output" in result and "choices" in result["output"]:
                return result["output"]["choices"][0]["text"].strip()
            
            logger.error(f"Unexpected API response: {result}")
            return "I'm having trouble generating a response. Please try again."
            
        except requests.Timeout:
            logger.error("API request timed out")
            return "The request took too long. Please try again."
            
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return "I'm having trouble connecting to the service. Please try again shortly."
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return "Something went wrong. Please try again."
