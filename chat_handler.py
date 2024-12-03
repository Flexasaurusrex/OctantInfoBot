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
        
        self.system_prompt = """You are a helpful assistant that provides information about Octant, 
        a developer-centric web interface for Kubernetes clusters. You should focus on helping users 
        understand Octant's features, capabilities, and how it can help them manage and visualize 
        their Kubernetes clusters. Be concise but informative in your responses."""
        
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
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            if "output" in result:
                return result["output"]["choices"][0]["text"].strip()
            else:
                return "I apologize, but I couldn't generate a response at the moment. Please try again."
                
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I apologize, but I encountered an error while processing your request. Please try again later."
