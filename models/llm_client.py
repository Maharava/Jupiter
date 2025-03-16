import requests
import json
import random
import datetime

class LLMClient:
    """Client for interacting with LLM providers like Ollama"""
    
    def __init__(self, api_url="http://localhost:11434", default_model="llama3", test_mode=False):
        """Initialize LLM client with API URL and default model"""
        self.api_url = api_url
        self.default_model = default_model
        self.test_mode = test_mode
        
        # Test mode responses
        self.test_responses = [
            "TEST MODE: This is a placeholder response for testing purposes.",
            "TEST MODE: Jupiter is running in offline test mode. No LLM is being called.",
            "TEST MODE: I'm a simulated response. No AI model is generating this text.",
            "TEST MODE: I'm currently in offline testing mode without access to an LLM backend.",
            "TEST MODE: This is an automated response. The system is in testing mode."
        ]
        
        if self.test_mode:
            print(f"🧪 LLMClient initialized in TEST MODE - No actual LLM calls will be made")
    
    def generate_chat_response(self, prompt, temperature=0.7, top_p=0.9, top_k=40, max_tokens=None):
        """Generate a chat response from the LLM"""
        if self.test_mode:
            # In test mode, return a predefined response
            return self._generate_test_response(prompt)
            
        try:
            payload = {
                "model": self.default_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "top_k": top_k
                }
            }
            
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
                
            endpoint = f"{self.api_url}/api/generate"
            response = requests.post(endpoint, json=payload, timeout=60)
            
            if response.status_code == 200:
                response_json = response.json()
                if 'response' in response_json:
                    return response_json['response'].strip()
                else:
                    return "Error: Unexpected response format from LLM API."
            else:
                return f"Error: Could not connect to LLM API (Status: {response.status_code})."
                    
        except Exception as e:
            return f"Error communicating with LLM: {str(e)}"
    
    def _generate_test_response(self, prompt):
        """Generate a test response with some basic context awareness"""
        # Get a random response from the test responses
        base_response = random.choice(self.test_responses)
        
        # Add timestamp for uniqueness
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Extract user's message for minimal context
        last_user_message = "your message"
        if ":" in prompt:
            # Try to extract the last user message from the prompt
            parts = prompt.split("\n")
            for part in reversed(parts):
                if ":" in part and not part.startswith("Jupiter:"):
                    last_user_message = part.split(":", 1)[1].strip()
                    # Truncate if too long
                    if len(last_user_message) > 30:
                        last_user_message = last_user_message[:27] + "..."
                    break
        
        # Combine elements for a semi-contextual response
        return f"{base_response}\n\nTimestamp: {timestamp}\nReceived: \"{last_user_message}\"\n\nThis is a simulated response for testing the UI and functionality without requiring an LLM connection."
    
    def extract_information(self, extraction_prompt, conversation_text, temperature=0.2):
        """Use the LLM to extract information from conversation text"""
        if self.test_mode:
            # In test mode, return a minimal JSON response
            return '{"extracted_info": []}'
            
        try:
            # Format complete prompt for extraction
            prompt = f"{extraction_prompt}\n\nHere is the conversation to analyze:\n\n{conversation_text}\n\nExtracted information:"
            
            payload = {
                "model": self.default_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            endpoint = f"{self.api_url}/api/generate"
            response = requests.post(endpoint, json=payload, timeout=60)
            
            if response.status_code == 200:
                response_json = response.json()
                if 'response' in response_json:
                    return response_json['response'].strip()
                else:
                    print(f"Error: Unexpected response format from LLM API.")
                    return None
            else:
                print(f"Error: Could not connect to LLM API (Status: {response.status_code}).")
                return None
                    
        except Exception as e:
            print(f"Error communicating with LLM: {str(e)}")
            return None