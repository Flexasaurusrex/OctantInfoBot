import os
import requests

class ChatHandler:
    def __init__(self):
        self.api_key = os.environ["TOGETHER_API_KEY"]
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.base_prompt = """You are a helpful assistant for Octant, a platform for experiments in participatory public goods funding. 
Your role is to provide accurate, concise information about Octant's features, processes, and governance.
Use a friendly, professional tone and keep responses clear and focused.

Current conversation:
{conversation}
User: {message}
Assistant:"""
        self.conversation_history = []
        
    def get_response(self, message):
        """Generate a response using the Together API"""
        try:
            # Keep conversation history limited
            self.conversation_history = self.conversation_history[-4:]  # Keep last 4 exchanges
            
            # Format conversation history
            conversation = "\n".join([f"User: {ex['user']}\nAssistant: {ex['assistant']}" 
                                    for ex in self.conversation_history])
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "prompt": self.base_prompt.format(
                    conversation=conversation,
                    message=message
                ),
                "max_tokens": 800,
                "temperature": 0.7,
                "top_p": 0.7,
                "stop": ["User:", "Assistant:"]
            }
            
            # Make API request
            response = requests.post(
                "https://api.together.xyz/inference",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            # Process response
            response_data = response.json()
            if 'output' in response_data and 'text' in response_data['output']:
                assistant_response = response_data['output']['text'].strip()
                
                # Update conversation history
                self.conversation_history.append({
                    'user': message,
                    'assistant': assistant_response
                })
                
                return assistant_response
            else:
                print(f"Unexpected response structure: {response_data.keys()}")
                return "I apologize, but I'm having trouble processing your request. Please try again."
                
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I encountered an error. Please try asking your question again."
