import os
import time
import datetime
import random
import requests
import re
import json
from colorama import init, Fore, Style

from curiosity_manager import CuriosityManager
from initial_greeting import initial_greeting
from improved_info_extraction import extract_personal_info

# Initialize colorama
init()

# Define colors
JUPITER_COLOR = Fore.YELLOW
USER_COLOR = Fore.MAGENTA

class JupiterChat:
    def __init__(self, kobold_api_url="http://localhost:5001", 
                 token_limit=8192, 
                 prompt_folder="prompt",
                 logs_folder="logs",
                 user_data_file="user_data.json"):
        
        self.kobold_api_url = kobold_api_url
        self.token_limit = token_limit
        self.prompt_folder = prompt_folder
        self.logs_folder = logs_folder
        self.user_data_file = user_data_file
        self.conversation_history = []
        self.current_log_file = None
        
        # Define colors as instance variables for external access
        self.JUPITER_COLOR = JUPITER_COLOR
        self.USER_COLOR = USER_COLOR
        self.Style = Style
        
        # Create folders if they don't exist
        os.makedirs(prompt_folder, exist_ok=True)
        os.makedirs(logs_folder, exist_ok=True)
        
        # Create an empty user_data file if it doesn't exist
        if not os.path.exists(user_data_file):
            with open(user_data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        
        # Initialize empty user data
        self.user_data = {}
        
        # Create curiosity manager
        self.curiosity = CuriosityManager(self)
        
        # Set up token counter
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            self.use_tiktoken = True
        except ImportError:
            self.use_tiktoken = False
    
    def count_tokens(self, text):
        """Count tokens in text"""
        if self.use_tiktoken:
            return len(self.tokenizer.encode(text))
        else:
            # Simple approximation
            return len(re.findall(r'\w+|[^\w\s]', text))
    
    def load_system_prompt(self):
        """Load system prompt from file"""
        system_prompt_path = os.path.join(self.prompt_folder, "system_prompt.txt")
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Create default prompt if none exists
            default_prompt = "You are Jupiter, a helpful AI assistant."
            with open(system_prompt_path, 'w', encoding='utf-8') as f:
                f.write(default_prompt)
            return default_prompt
    
    def load_user_data(self):
        """Load user data from file"""
        if os.path.exists(self.user_data_file):
            with open(self.user_data_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        else:
            return {}
    
    def save_user_data(self):
        """Save user data to file"""
        # Get the full data structure
        data = self.load_user_data()
        
        # Make sure known_users exists
        if 'known_users' not in data:
            data['known_users'] = {}
        
        # Get the user's name
        if 'name' in self.user_data:
            # Update the user's data in the known_users section
            data['known_users'][self.user_data['name']] = self.user_data
        
        # Save the entire structure
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    
    def update_user_data(self, message):
        """Update user data using improved extraction"""
        # Extract info using the improved function
        updates, personal_info_shared = extract_personal_info(message, self.user_data)
        
        # Update user_data with any new information
        if updates:
            self.user_data.update(updates)
            self.save_user_data()
            
            # Update curiosity manager with new knowledge
            self.curiosity.update_known_info()
            
            # Update trust level if personal info was shared
            if personal_info_shared:
                self.curiosity.update_trust_level(len(message), personal_info_shared)
        
        return personal_info_shared
    
    def get_user_prefix(self):
        """Return user prefix based on known name"""
        return f"{self.user_data['name']}:" if 'name' in self.user_data else "User:"
    
    def prepare_message_for_llm(self, user_input):
        """Prepare complete message for LLM with history and prompt"""
        system_prompt = self.load_system_prompt()
        
        # Get LLM curiosity prompt if appropriate
        curiosity_prompt = ""
        if self.curiosity.should_ask_question() and random.random() < 0.5:  # 50% chance of LLM question vs direct
            curiosity_prompt = self.curiosity.get_llm_curiosity_prompt()
            if curiosity_prompt:
                self.curiosity.messages_since_last_question = 0
                self.curiosity.questions_this_session += 1
        
        # Add curiosity instruction to system prompt if needed
        if curiosity_prompt:
            full_prompt = f"{system_prompt}\n\n{curiosity_prompt}"
        else:
            full_prompt = system_prompt
        
        # Combine system prompt and history
        full_message = full_prompt + "\n\n"
        for msg in self.conversation_history:
            full_message += msg + "\n"
        
        # Add current user input
        full_message += f"{self.get_user_prefix()} {user_input}\nJupiter:"
        
        # Truncate if exceeding token limit
        if self.count_tokens(full_message) > self.token_limit:
            while self.count_tokens(full_message) > self.token_limit and len(self.conversation_history) > 1:
                self.conversation_history.pop(0)  # Remove oldest message
                
                # Rebuild message
                full_message = full_prompt + "\n\n"
                for msg in self.conversation_history:
                    full_message += msg + "\n"
                full_message += f"{self.get_user_prefix()} {user_input}\nJupiter:"
        
        return full_message
    
    def send_to_kobold(self, message):
        """Send message to KoboldCPP and return response"""
        try:
            payload = {
                "prompt": message,
                "max_length": 200,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "rep_pen": 1.1,
                "stop": ["User:", self.get_user_prefix(), "Jupiter:"]
            }
            
            endpoint = f"{self.kobold_api_url}/api/v1/generate"
            response = requests.post(endpoint, json=payload, timeout=60)
            
            if response.status_code == 200:
                response_json = response.json()
                if 'results' in response_json and len(response_json['results']) > 0:
                    return response_json['results'][0]['text'].strip()
                else:
                    return "Error: Unexpected response format from KoboldCPP API."
            else:
                return f"Error: Could not connect to KoboldCPP API (Status: {response.status_code})."
                
        except Exception as e:
            return f"Error communicating with KoboldCPP: {str(e)}"
    
    def start_new_log(self):
        """Create new log file for session"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.current_log_file = os.path.join(self.logs_folder, f"jupiter_chat_{timestamp}.log")
        
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Jupiter Chat Session: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
    
    def log_message(self, role, message):
        """Log message to current log file"""
        if self.current_log_file:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {role} {message}\n\n")
    
    def run(self):
        """Run chat interface"""
        print("=== Jupiter Chat ===")
        
        # Start logging
        self.start_new_log()
        
        # Handle initial greeting and user identification
        initial_greeting(self)
        
        print("Type 'exit' or 'quit' to end the conversation.")
        
        while True:
            # Get user input with colored prefix
            user_prefix = self.get_user_prefix()
            user_input = input(f"{USER_COLOR}{user_prefix}{Style.RESET_ALL} ")
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit']:
                print(f"{JUPITER_COLOR}Jupiter:{Style.RESET_ALL} Ending chat session. Goodbye!")
                break
            
            # Update user data with any extracted info
            self.update_user_data(user_input)
            
            # Log user message
            self.log_message(user_prefix, user_input)
            
            # Add to history
            self.conversation_history.append(f"{user_prefix} {user_input}")
            
            # Prepare and send to LLM
            llm_message = self.prepare_message_for_llm(user_input)
            response = self.send_to_kobold(llm_message)
            
            # Print and log response with color
            print(f"{JUPITER_COLOR}Jupiter:{Style.RESET_ALL} {response}")
            self.log_message("Jupiter:", response)
            
            # Add to history
            self.conversation_history.append(f"Jupiter: {response}")
            
            # Increment messages since last question
            self.curiosity.messages_since_last_question += 1
            
            # Check for date mentions that might need follow-up
            date_mention = self.curiosity.check_for_date_mentions(user_input)
            if date_mention and 'important_dates' not in self.user_data:
                date_follow_up = self.curiosity.generate_date_follow_up(date_mention)
                
                # Small delay to make it feel natural
                time.sleep(1.5)
                
                # Print and log follow-up question
                print(f"{JUPITER_COLOR}Jupiter:{Style.RESET_ALL} {date_follow_up}")
                self.log_message("Jupiter:", date_follow_up)
                
                # Add to history
                self.conversation_history.append(f"Jupiter: {date_follow_up}")
                
                # Reset curiosity counters
                self.curiosity.messages_since_last_question = 0
                self.curiosity.questions_this_session += 1
                continue
            
            # Maybe ask a direct curious question
            if self.curiosity.should_ask_question():
                curious_question = self.curiosity.generate_direct_question()
                if curious_question:
                    # Small delay to make it feel natural
                    time.sleep(1.5)
                    
                    # Print and log curious question
                    print(f"{JUPITER_COLOR}Jupiter:{Style.RESET_ALL} {curious_question}")
                    self.log_message("Jupiter:", curious_question)
                    
                    # Add to history
                    self.conversation_history.append(f"Jupiter: {curious_question}")