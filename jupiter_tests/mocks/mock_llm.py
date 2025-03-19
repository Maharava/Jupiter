import json
import random
import datetime
import re
from unittest.mock import MagicMock

class MockLLMClient:
    """Mock LLM client that returns predefined responses"""
    
    def __init__(self, api_url=None, default_model=None, test_mode=True):
        """Initialize with predetermined responses"""
        self.api_url = api_url or "http://mock_api_url"
        self.default_model = default_model or "mock_model"
        self.test_mode = True  # Always in test mode
        
        # Predefined responses
        self.chat_responses = [
            "I'm Jupiter, your AI assistant. How can I help you today?",
            "That's an interesting question! Let me think about that.",
            "I understand what you're asking. Here's what I know about that topic.",
            "I'd be happy to help with that. Let me provide some information."
        ]
        
        # Special responses for specific inputs
        self.special_responses = {
            # Matches for common queries
            r'(?i).*what.*time.*': "The current time is {time}.",
            r'(?i).*weather.*': "I don't have real-time weather data, but I'd be happy to discuss something else.",
            r'(?i).*name.*': "I'm Jupiter, your friendly AI assistant.",
            r'(?i).*your.*purpose.*': "I'm here to have helpful, thoughtful conversations and assist with information and tasks.",
            r'(?i).*help.*': "I'd be happy to help! What would you like to know about?",
            r'(?i).*calendar.*': "I can help you manage your calendar. You can add events, check your schedule, and set reminders.",
            r'(?i).*meeting.*': "I see you're asking about meetings. Would you like to schedule one or get information about an existing meeting?",
            r'(?i).*memory.*': "I remember the information you've shared with me during our conversations. It helps me provide more personalized responses."
        }
        
        # Extraction responses for common information
        self.extraction_patterns = [
            {
                "pattern": r'(?i).*name is (\w+).*',
                "response": '{"extracted_info": [{"category": "name", "value": "{match_1}"}]}'
            },
            {
                "pattern": r'(?i).*from (\w+).*',
                "response": '{"extracted_info": [{"category": "location", "value": "{match_1}"}]}'
            },
            {
                "pattern": r'(?i).*like(?:s)? ([\w\s]+).*',
                "response": '{"extracted_info": [{"category": "likes", "value": "{match_1}"}]}'
            },
            {
                "pattern": r'(?i).*(?:don\'t|doesn\'t|not) like ([\w\s]+).*',
                "response": '{"extracted_info": [{"category": "dislikes", "value": "{match_1}"}]}'
            },
            {
                "pattern": r'(?i).*(?:work|job|profession).*(\w+).*',
                "response": '{"extracted_info": [{"category": "profession", "value": "{match_1}"}]}'
            }
        ]
        
        # Default extraction response (nothing found)
        self.default_extraction = '{"extracted_info": []}'
    
    def generate_chat_response(self, prompt, temperature=0.7, top_p=0.9, top_k=40, max_tokens=None):
        """Generate a chat response based on the prompt"""
        # Check for special responses first
        for pattern, response_template in self.special_responses.items():
            if re.search(pattern, prompt):
                # Format the response template if needed
                if "{time}" in response_template:
                    current_time = datetime.datetime.now().strftime("%I:%M %p")
                    return response_template.format(time=current_time)
                return response_template
        
        # Look for user information to personalize response
        user_matches = re.search(r'name: (\w+)', prompt)
        user_name = user_matches.group(1) if user_matches else "there"
        
        # For system prompts that don't match special patterns, return general responses
        if "Jupiter:" in prompt.splitlines()[-1]:
            # This is likely a chat prompt expecting Jupiter's response
            return random.choice(self.chat_responses)
        
        # Default response
        return f"Hello {user_name}, I'm Jupiter. How can I help you today?"
    
    def extract_information(self, extraction_prompt, conversation_text, temperature=0.2):
        """Mock information extraction from conversation text"""
        # Check each pattern to see if we can extract information
        for pattern_info in self.extraction_patterns:
            matches = re.search(pattern_info["pattern"], conversation_text)
            if matches:
                # Format the response template with the match groups
                response = pattern_info["response"]
                for i, group in enumerate(matches.groups(), 1):
                    response = response.replace(f"{{match_{i}}}", group.strip())
                return response
        
        # Default response if no patterns matched
        return self.default_extraction
