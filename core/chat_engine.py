import os
import json
import datetime

from utils.text_processing import count_tokens, truncate_to_token_limit

class ChatEngine:
    """Core chat functionality for Jupiter"""
    
    def __init__(self, llm_client, user_model, logger, ui, config):
        """Initialize chat engine with dependencies"""
        self.llm_client = llm_client
        self.user_model = user_model
        self.logger = logger
        self.ui = ui
        self.config = config
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Create necessary folders
        os.makedirs(config['paths']['prompt_folder'], exist_ok=True)
        os.makedirs(config['paths']['logs_folder'], exist_ok=True)
    
    def load_system_prompt(self):
        """Load system prompt from file"""
        system_prompt_path = os.path.join(self.config['paths']['prompt_folder'], "system_prompt.txt")
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Create default prompt if none exists
            default_prompt = "You are Jupiter, a helpful AI assistant."
            with open(system_prompt_path, 'w', encoding='utf-8') as f:
                f.write(default_prompt)
            return default_prompt
    
    def format_user_information(self):
        """Format known user information for inclusion in system prompt"""
        user_info = self.user_model.current_user
        
        if not user_info or len(user_info) <= 1:  # Only contains name
            return ""
            
        # Start with header
        formatted_info = "\n\n## What You Know About The User\n"
        
        # Basic identity information
        formatted_info += f"- Name: {user_info.get('name', 'Unknown')}\n"
        
        # Add other information categories
        for category, value in user_info.items():
            # Skip name as it's already added
            if category == 'name':
                continue
                
            # Format lists (likes, interests, etc.)
            if isinstance(value, list) and value:
                formatted_info += f"- {category.capitalize()}: {', '.join(value)}\n"
            # Format simple key-value pairs
            elif value and not isinstance(value, list):
                formatted_info += f"- {category.capitalize()}: {value}\n"
        
        return formatted_info
    
    def prepare_message_for_llm(self, user_input):
        """Prepare complete message for LLM with history and prompt"""
        system_prompt = self.load_system_prompt()
        
        # Add user information to system prompt
        user_info = self.format_user_information()
        enhanced_system_prompt = system_prompt + user_info
        
        user_prefix = f"{self.user_model.current_user.get('name', 'User')}:"
        
        # Add current user input
        current_input = f"{user_prefix} {user_input}\nJupiter:"
        
        # Truncate history if needed to stay within token limit
        preserved_history = truncate_to_token_limit(
            current_input, 
            self.conversation_history,
            enhanced_system_prompt,
            self.config['llm']['token_limit']
        )
        
        # Build the full message
        full_message = enhanced_system_prompt + "\n\n"
        for msg in preserved_history:
            full_message += msg + "\n"
        full_message += current_input
        
        return full_message
    
    def get_user_prefix(self):
        """Return user prefix based on known name"""
        return f"{self.user_model.current_user.get('name', 'User')}:"
    
    def format_memory_display(self):
        """Format user memory information for display to the user"""
        user_info = self.user_model.current_user
        
        # Start with header
        memory_display = "Here's what I remember about you:\n\n"
        
        if not user_info or len(user_info) <= 1:  # Only contains name
            memory_display += "I don't have much information about you yet beyond your name.\n"
            return memory_display
            
        # Group information by categories
        categories = {
            "Basic Information": ["name", "age", "gender", "location", "profession"],
            "Preferences": ["likes", "dislikes", "interests", "hobbies"],
            "Context": ["family", "goals", "important_dates"]
        }
        
        # Track which keys we've processed
        processed_keys = set()
        
        # Add information by category groups
        for category_group, keys in categories.items():
            # Check if we have any information in this category
            has_info = any(key in user_info for key in keys)
            
            if has_info:
                memory_display += f"## {category_group}\n"
                
                for key in keys:
                    if key in user_info and user_info[key]:
                        processed_keys.add(key)
                        
                        # Format lists (likes, interests, etc.)
                        if isinstance(user_info[key], list) and user_info[key]:
                            memory_display += f"- {key.capitalize()}: {', '.join(user_info[key])}\n"
                        # Format simple key-value pairs
                        elif user_info[key] and not isinstance(user_info[key], list):
                            memory_display += f"- {key.capitalize()}: {user_info[key]}\n"
                
                memory_display += "\n"
        
        # Add any remaining information that wasn't in the predefined categories
        remaining_keys = [key for key in user_info.keys() if key not in processed_keys]
        
        if remaining_keys:
            memory_display += "## Other Information\n"
            
            for key in remaining_keys:
                if user_info[key]:
                    # Format lists
                    if isinstance(user_info[key], list) and user_info[key]:
                        memory_display += f"- {key.capitalize()}: {', '.join(user_info[key])}\n"
                    # Format simple key-value pairs
                    elif user_info[key] and not isinstance(user_info[key], list):
                        memory_display += f"- {key.capitalize()}: {user_info[key]}\n"
        
        return memory_display
    
    def handle_user_commands(self, user_input):
        """Handle special user commands for managing identity"""
        if user_input.startswith('/name '):
            # Command to change username
            new_name = user_input[6:].strip()
            if new_name:
                # Update user name
                self.user_model.current_user['name'] = new_name
                self.user_model.save_current_user()
                return f"I'll call you {new_name} from now on."
            else:
                return "Please provide a name after the /name command."
        
        elif user_input == '/memory':
            # Show what Jupiter remembers about the user
            return self.format_memory_display()
        
        elif user_input == '/help':
            # Show available commands
            return """
Available commands:
/name [new name] - Change your name
/memory - Show what I remember about you
/help - Show this help message
            """
        
        # Not a command, return None to continue normal processing
        return None
    
    def handle_initial_greeting(self):
        """Handle the initial greeting and user identification"""
        # Start a new log file
        self.logger.start_new_log()
        
        # Ask for name
        self.ui.print_jupiter_message("I'm Jupiter, your AI assistant. Please enter your name. Please ONLY type your name in. Consider it a username.")
        
        while True:
            name = self.ui.get_user_input()
            
            # Check for exit command
            if self.ui.handle_exit_command(name):
                self.ui.exit_program()
            
            # If a name was entered, proceed
            if name:
                break
            else:
                self.ui.print_jupiter_message("Please enter a name or type 'exit' to quit.")
        
        # Load all user data
        all_user_data = self.user_model.load_all_users()
        
        # Check if this is a returning user (case insensitive)
        if 'known_users' in all_user_data:
            # Convert all stored names to lowercase for comparison
            name_map = {user_name.lower(): user_name for user_name in all_user_data['known_users']}
            
            # Check if the lowercase version of the entered name exists
            if name.lower() in name_map:
                # Use the properly capitalized name from the stored data
                actual_name = name_map[name.lower()]
                
                # Load user data
                user_data = all_user_data['known_users'][actual_name]
                self.user_model.set_current_user(user_data)
                
                self.ui.print_jupiter_message(f"Welcome back, {actual_name}! It's great to chat with you again.")
                return
        
        # New user
        self.user_model.set_current_user({'name': name})
        self.user_model.save_current_user()
        self.ui.print_jupiter_message(f"Nice to meet you, {name}! How can I help you today?")
    
    def restart_chat(self):
        """Restart the chat session while preserving user data"""
        # Log that we're restarting
        self.logger.log_message("System:", "Chat session restarted by user")
        
        # Save current log file
        current_log = self.logger.get_current_log_file()
        
        # Start a new log file
        self.logger.start_new_log()
        
        # Clear conversation history
        self.conversation_history = []
        
        # Clear the UI if it's a GUI
        if hasattr(self.ui, 'clear_chat'):
            self.ui.clear_chat()
            self.ui.set_status("Restarting chat...", True)
        
        # Show welcome message
        self.ui.print_jupiter_message("=== Jupiter Chat Restarted ===")
        self.ui.print_jupiter_message(f"Hello again, {self.user_model.current_user.get('name', 'User')}! How can I help you today?")
        
        # Reset status if it's a GUI
        if hasattr(self.ui, 'set_status'):
            self.ui.set_status("Ready")
    
    def show_knowledge(self):
        """Show knowledge base information (placeholder for now)"""
        if hasattr(self.ui, 'set_status'):
            self.ui.set_status("Loading knowledge...", True)
            
        # Display memory information for now
        knowledge_info = self.format_memory_display()
        self.ui.print_jupiter_message(knowledge_info)
        
        if hasattr(self.ui, 'set_status'):
            self.ui.set_status("Ready")
    
    def run(self):
        """Run the chat interface"""
        # Print welcome message
        self.ui.print_welcome()
        
        # Set up button callbacks if using GUI
        if hasattr(self.ui, 'set_restart_callback'):
            self.ui.set_restart_callback(self.restart_chat)
            self.ui.set_knowledge_callback(self.show_knowledge)
        
        # Show processing status if GUI is used
        if hasattr(self.ui, 'set_status'):
            self.ui.set_status("Processing logs...", True)
            
        # Handle initial greeting and user identification
        self.handle_initial_greeting()
        
        # Print exit instructions
        self.ui.print_exit_instructions()
        
        # Reset status
        if hasattr(self.ui, 'set_status'):
            self.ui.set_status("Ready")
        
        # Main chat loop
        while True:
            # Get user input
            user_prefix = self.get_user_prefix()
            user_input = self.ui.get_user_input(user_prefix[:-1])  # Remove colon from prefix
            
            # Check for exit command
            if self.ui.handle_exit_command(user_input):
                break
            
            # Set busy status
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Processing your request...", True)
            
            # Check for user commands
            command_response = self.handle_user_commands(user_input)
            if command_response:
                self.ui.print_jupiter_message(command_response)
                self.logger.log_message("Jupiter:", command_response)
                
                # Reset status
                if hasattr(self.ui, 'set_status'):
                    self.ui.set_status("Ready")
                    
                continue
            
            # Log user message
            self.logger.log_message(user_prefix, user_input)
            
            # Add to history
            self.conversation_history.append(f"{user_prefix} {user_input}")
            
            # Update status to show Jupiter is generating a response
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Thinking...", True)
            
            # Prepare and send to LLM
            llm_message = self.prepare_message_for_llm(user_input)
            response = self.llm_client.generate_chat_response(
                llm_message, 
                temperature=self.config['llm']['chat_temperature']
            )
            
            # Print and log response
            self.ui.print_jupiter_message(response)
            self.logger.log_message("Jupiter:", response)
            
            # Add to history
            self.conversation_history.append(f"Jupiter: {response}")
            
            # Reset status
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Ready")