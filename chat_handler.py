import os
import json
import requests

class ChatHandler:
    def __init__(self):
        self.api_key = os.environ.get("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY environment variable is not set")
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.base_url = "https://api.together.xyz/inference"
        
        self.system_prompt = """You are a helpful assistant that provides information about Octant Public Goods (https://octant.build/). 
        Octant is a public goods organization focused on solving critical coordination problems in web3 through 
        innovative incentive mechanisms and governance solutions.

        Focus on Octant's key areas:
        - Public goods funding and coordination
        - Incentive mechanism design
        - Web3 governance solutions
        - Community-driven initiatives
        - Research and development in web3 space

        Only provide information about Octant Public Goods (https://octant.build/), not any other meanings or uses of 
        the word 'octant'. Be concise but informative in your responses."""
        
    def get_response(self, user_message):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""<s>[INST] {self.system_prompt}

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
        
        try:
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
                return response_text
            else:
                print("Unexpected API response format:", result)
                return "I apologize, but I couldn't generate a response at the moment. Please try again."
                
        except requests.exceptions.Timeout:
            print("API request timed out")
            return "I apologize, but the request took too long to process. Please try again."
            
        except requests.exceptions.RequestException as e:
            print(f"API request error: {str(e)}")
            return "I apologize, but I encountered an error while processing your request. Please try again later."
            
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return "I apologize, but something unexpected happened. Please try again later."
