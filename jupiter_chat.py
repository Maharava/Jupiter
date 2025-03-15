import os
import time
import datetime
import random
import requests
import re
import json
from colorama import init, Fore, Style

# Import the InfoExtractor
from info_extractor import InfoExtractor

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
        
        # Initialize the InfoExtractor
        self.info_extractor = InfoExtractor(self, kobold_api_url=kobold_api_url)
        
        # Process unprocessed logs during startup
        print("Processing previous conversation logs...")
        self.info_extractor.process_all_unprocessed_logs()
        
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
    
    def identify_user(self, username=None):
        """Simple user identification without data extraction"""
        if username and username.strip():
            self.user_data['name'] = username.strip()
            self.save_user_data()
        return self.user_data.get('name', 'User')
    
    def get_user_prefix(self):
        """Return user prefix based on known name"""
        return f"{self.user_data['name']}:" if 'name' in self.user_data else "User:"
    
    def prepare_message_for_llm(self, user_input):
        """Prepare complete message for LLM with history and prompt"""
        system_prompt = self.load_system_prompt()
        
        # Combine system prompt and history
        full_message = system_prompt + "\n\n"
        for msg in self.conversation_history:
            full_message += msg + "\n"
        
        # Add current user input
        full_message += f"{self.get_user_prefix()} {user_input}\nJupiter:"
        
        # Truncate if exceeding token limit
        if self.count_tokens(full_message) > self.token_limit:
            while self.count_tokens(full_message) > self.token_limit and len(self.conversation_history) > 1:
                self.conversation_history.pop(0)  # Remove oldest message
                
                # Rebuild message
                full_message = system_prompt + "\n\n"
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
    
    def handle_initial_greeting(self):
        """Simplified initial greeting to only identify the user"""
        # Check if any users exist in the system
        data = self.load_user_data()
        
        if 'known_users' in data and data['known_users']:
            # We have returning users, ask if they're returning
            print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} Hi there! Have we talked before? (yes/no)")
            response = input(f"{self.USER_COLOR}User:{self.Style.RESET_ALL} ").strip().lower()
            
            if response in ['yes', 'y', 'yeah', 'yep', 'yup']:
                # Ask for name to identify returning user
                print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} Great to see you again! What's your name so I can load your information?")
                name = input(f"{self.USER_COLOR}User:{self.Style.RESET_ALL} ").strip()
                
                # Try to find user in known_users
                if 'known_users' in data:
                    matching_users = [u for u in data['known_users'] if u.lower() == name.lower()]
                    if matching_users:
                        # Use the proper capitalization of the name
                        name = matching_users[0]
                        # Load user data
                        self.user_data = data['known_users'][name].copy()
                        self.identify_user(name)
                        
                        print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} Welcome back, {name}! It's great to chat with you again.")
                        return
                
                print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} I don't seem to have a record for that name. Let's start fresh!")
                # Continue to new user flow
            else:
                print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} No problem! Let's get to know each other.")
                # Continue to new user flow
        
        # New user flow - ask for name only
        print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} I'm Jupiter, your AI assistant. What's your name?")
        name = input(f"{self.USER_COLOR}User:{self.Style.RESET_ALL} ").strip()
        
        # Set up new user with just a name
        self.identify_user(name)
        print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} Nice to meet you, {name}! How can I help you today?")
    
    def handle_user_commands(self, user_input):
        """Handle special user commands for managing identity"""
        if user_input.startswith('/name '):
            # Command to change username
            new_name = user_input[6:].strip()
            if new_name:
                self.identify_user(new_name)
                return f"I'll call you {new_name} from now on."
            else:
                return "Please provide a name after the /name command."
        
        elif user_input == '/help':
            # Show available commands
            return """
Available commands:
/name [new name] - Change your name
/help - Show this help message
            """
        
        # Not a command, return None to continue normal processing
        return None
    
    def run(self):
        """Run chat interface"""
        print("=== Jupiter Chat ===")
        
        # Start logging
        self.start_new_log()
        
        # Handle initial greeting and user identification
        self.handle_initial_greeting()
        
        print("Type 'exit' or 'quit' to end the conversation.")
        
        while True:
            # Get user input with colored prefix
            user_prefix = self.get_user_prefix()
            user_input = input(f"{self.USER_COLOR}{user_prefix}{self.Style.RESET_ALL} ")
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit']:
                print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} Ending chat session. Goodbye!")
                break
            
            # Check for user commands
            command_response = self.handle_user_commands(user_input)
            if command_response:
                print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} {command_response}")
                self.log_message("Jupiter:", command_response)
                continue
            
            # Log user message
            self.log_message(user_prefix, user_input)
            
            # Add to history
            self.conversation_history.append(f"{user_prefix} {user_input}")
            
            # Prepare and send to LLM
            llm_message = self.prepare_message_for_llm(user_input)
            response = self.send_to_kobold(llm_message)
            
            # Print and log response with color
            print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} {response}")
            self.log_message("Jupiter:", response)
            
            # Add to history
            self.conversation_history.append(f"Jupiter: {response}")