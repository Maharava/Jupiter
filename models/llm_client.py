import requests
import json

class LLMClient:
    """Client for interacting with LLM providers like Ollama"""
    
    def __init__(self, api_url="http://localhost:11434", default_model="llama3"):
        """Initialize LLM client with API URL and default model"""
        self.api_url = api_url
        self.default_model = default_model
    
    def generate_chat_response(self, prompt, temperature=0.7, top_p=0.9, top_k=40, max_tokens=None):
        """Generate a chat response from the LLM"""
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
    
    def extract_information(self, extraction_prompt, conversation_text, temperature=0.2):
        """Use the LLM to extract information from conversation text"""
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