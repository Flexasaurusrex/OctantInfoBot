import os
import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self):
        # API configuration
        self.api_key = os.environ.get("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY environment variable is not set")
        
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.base_url = "https://api.together.xyz/inference"
        
        # Session configuration with robust retry mechanism
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        
        # Rate limiting configuration
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def get_response(self, user_message: str) -> Tuple[bool, str]:
        """
        Get response from API with improved error handling.
        Returns a tuple of (success: bool, message: str)
        """
        if not user_message.strip():
            return False, "Please provide a message."
            
        try:
            self._enforce_rate_limit()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "prompt": f"User: {user_message.strip()}\n\nAssistant:",
                "max_tokens": 1024,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 50
            }
            
            logger.info(f"Sending request for message: {user_message[:50]}...")
            response = self.session.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"API returned status code {response.status_code}")
                return False, "I'm having trouble connecting to the service. Please try again."
            
            result = response.json()
            if "output" not in result or "choices" not in result["output"]:
                logger.error(f"Unexpected API response structure: {result}")
                return False, "I received an unexpected response. Please try again."
            
            response_text = result["output"]["choices"][0]["text"].strip()
            if not response_text:
                return False, "I couldn't generate a proper response. Please try again."
                
            logger.info(f"Successfully generated response: {response_text[:50]}...")
            return True, response_text
            
        except requests.Timeout:
            logger.error("API request timed out")
            return False, "The request took too long. Please try again in a moment."
            
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return False, "I'm having trouble connecting to the service. Please try again shortly."
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return False, "Something unexpected happened. Please try again."
