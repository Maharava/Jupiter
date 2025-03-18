import os
import json
import datetime

from utils.intent_recog import load_model, get_intent
from utils.voice_cmd import intent_functions
from utils.text_processing import count_tokens, truncate_to_token_limit
from utils.piper import llm_speak  # Import the original llm_speak function directly

class ChatEngine:
    """Core chat functionality for Jupiter"""
    
    def __init__(self, llm_client, user_model, logger, ui, config, test_mode=False):
        """Initialize chat engine with dependencies"""
        self.llm_client = llm_client
        self.user_model = user_model
        self.logger = logger
        self.ui = ui
        self.config = config
        self.test_mode = test_mode
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Create necessary folders
        os.makedirs(config['paths']['prompt_folder'], exist_ok=True)
        os.makedirs(config['paths']['logs_folder'], exist_ok=True)
        
        # Load intent recognition model
        try:
            self.intent_classifier, self.intent_vectorizer = load_model()
        except Exception as e:
            print(f"Failed to load intent model: {e}")
            self.intent_classifier = None
            self.intent_vectorizer = None
        
        if self.test_mode:
            print(f"🧪 ChatEngine initialized in TEST MODE")
    
    def load_system_prompt(self):
        """Load system prompt from file"""
        system_prompt_path = os.path.join(self.config['paths']['prompt_folder'], "system_prompt.txt")
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
                
                # Add test mode notice if in test mode
                if self.test_mode:
                    prompt += "\n\n## TEST MODE\nYou are currently running in offline test mode. No LLM backend is being used."
                    
                return prompt
        else:
            # Create default prompt if none exists
            default_prompt = "You are Jupiter, a helpful AI assistant."
            
            # Add test mode notice if in test mode
            if self.test_mode:
                default_prompt += "\n\n## TEST MODE\nYou are currently running in offline test mode. No LLM backend is being used."
            
            with open(system_prompt_path, 'w', encoding='utf-8') as f:
                f.write(default_prompt)
            return default_prompt
    
    def format_user_information(self):
        """Format user information for inclusion in system prompt"""
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
        """Format user memory information for display"""
        user_info = self.user_model.current_user
        
        # Start with header
        memory_display = "Here's what I remember about you:\n\n"
        
        # In test mode, add a notice
        if self.test_mode:
            memory_display = "TEST MODE: Here's what I remember about you (from test data):\n\n"
        
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
        """Handle special user commands"""
        if user_input.startswith('/name '):
            # Command to change username
            new_name = user_input[6:].strip()
            if new_name:
                # Update user name
                self.user_model.current_user['name'] = new_name
                self.user_model.save_current_user()
                response = f"I'll call you {new_name} from now on."
                llm_speak(response)  # Speak the response
                return response
            else:
                response = "Please provide a name after the /name command."
                llm_speak(response)  # Speak the response
                return response
        
        elif user_input == '/memory':
            # Show what Jupiter remembers about the user
            response = self.format_memory_display()
            llm_speak("Here's what I remember about you.")  # Simplified for speech
            return response
        
        elif user_input == '/help':
            # Show available commands
            help_text = """
Available commands:
/name [new name] - Change your name
/memory - Show what I remember about you
/help - Show this help message
            """
            
            # Add test mode info
            if self.test_mode:
                help_text += "\n⚠️ TEST MODE is active - running without LLM backend\n"
            
            llm_speak("Here are the available commands.")  # Simplified for speech
            return help_text
        
        # Not a command, return None to continue normal processing
        return None
    
    def handle_initial_greeting(self):
        """Handle initial greeting and user identification"""
        # Start a new log file
        self.logger.start_new_log()
        
        # Special test mode greeting if applicable
        test_mode_notice = ""
        if self.test_mode:
            test_mode_notice = " (TEST MODE - No LLM connection)"
        
        # Ask for name
        greeting = f"I'm Jupiter{test_mode_notice}, your AI assistant. Please enter your name. Please ONLY type your name in. Consider it a username."
        self.ui.print_jupiter_message(greeting)
        llm_speak("I'm Jupiter, your AI assistant. Please enter your name.")
        
        while True:
            name = self.ui.get_user_input()
            
            # Check for exit command
            if self.ui.handle_exit_command(name):
                self.ui.exit_program()
            
            # If a name was entered, proceed
            if name:
                break
            else:
                prompt = "Please enter a name or type 'exit' to quit."
                self.ui.print_jupiter_message(prompt)
                llm_speak(prompt)
        
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
                
                # Greeting with test mode notice if applicable
                welcome = f"Welcome back, {actual_name}! It's great to chat with you again."
                if self.test_mode:
                    welcome += " (TEST MODE ACTIVE)"
                
                self.ui.print_jupiter_message(welcome)
                llm_speak(f"Welcome back, {actual_name}! It's great to chat with you again.")
                    
                return
        
        # New user
        self.user_model.set_current_user({'name': name})
        self.user_model.save_current_user()
        
        # Greeting with test mode notice if applicable
        greeting = f"Nice to meet you, {name}! How can I help you today?"
        if self.test_mode:
            greeting += " (TEST MODE ACTIVE)"
        
        self.ui.print_jupiter_message(greeting)
        llm_speak(f"Nice to meet you, {name}! How can I help you today?")
    
    def restart_chat(self):
        """Restart chat session while preserving user data"""
        # Log that we're restarting
        self.logger.log_message("System:", "Chat session restarted by user")
        
        # Start a new log file
        self.logger.start_new_log()
        
        # Clear conversation history
        self.conversation_history = []
        
        # Clear the UI if it's a GUI
        if hasattr(self.ui, 'clear_chat'):
            self.ui.clear_chat()
            self.ui.set_status("Restarting chat...", True)
        
        # Special test mode notice if applicable
        test_mode_notice = ""
        if self.test_mode:
            test_mode_notice = " (TEST MODE ACTIVE)"
        
        # Show welcome message
        restart_message = f"=== Jupiter Chat Restarted{test_mode_notice} ==="
        self.ui.print_jupiter_message(restart_message)
        
        greeting = f"Hello again, {self.user_model.current_user.get('name', 'User')}! How can I help you today?"
        self.ui.print_jupiter_message(greeting)
        llm_speak(greeting)
        
        # Reset status if it's a GUI
        if hasattr(self.ui, 'set_status'):
            if self.test_mode:
                self.ui.set_status("TEST MODE - Ready")
            else:
                self.ui.set_status("Ready")
    
    def show_knowledge(self):
        """Show knowledge view with user information"""
        if hasattr(self.ui, 'set_status'):
            status_text = "Loading knowledge..."
            if self.test_mode:
                status_text = "TEST MODE - " + status_text
            self.ui.set_status(status_text, True)
            
        # Get user data from the model
        user_info = self.user_model.current_user
        
        # Send data to UI and show knowledge view
        self.ui.create_knowledge_bubbles(user_info)
        self.ui.show_knowledge_view()
        
        # Speak notification
        llm_speak("Showing your knowledge profile.")
        
        # Reset status
        if hasattr(self.ui, 'set_status'):
            status_text = "Viewing Knowledge"
            if self.test_mode:
                status_text = "TEST MODE - " + status_text
            self.ui.set_status(status_text, False)
            
    def process_knowledge_edits(self):
        """Process knowledge edits from the UI"""
        # Check if the UI has a knowledge edit queue
        if not hasattr(self.ui, 'knowledge_edit_queue'):
            return
            
        # Process all edits in the queue
        edits_processed = False
        while not self.ui.knowledge_edit_queue.empty():
            edit = self.ui.knowledge_edit_queue.get()
            
            # Handle different edit types
            if edit["action"] == "edit":
                # Update simple value
                self.user_model.current_user[edit["category"]] = edit["new_value"]
                print(f"Updated {edit['category']} from '{edit['old_value']}' to '{edit['new_value']}'")
                edits_processed = True
                    
            elif edit["action"] == "remove":
                # Remove category entirely
                if edit["category"] in self.user_model.current_user:
                    del self.user_model.current_user[edit["category"]]
                    print(f"Removed {edit['category']}")
                    edits_processed = True
                    
            elif edit["action"] == "add_list_item":
                # Add item to list
                category = edit["category"]
                new_item = edit["value"]
                
                # Create list if it doesn't exist
                if category not in self.user_model.current_user:
                    self.user_model.current_user[category] = []
                    
                # Add item if it's not already in the list
                if new_item not in self.user_model.current_user[category]:
                    self.user_model.current_user[category].append(new_item)
                    print(f"Added '{new_item}' to {category}")
                    edits_processed = True
                    
            elif edit["action"] == "remove_list_item":
                # Remove item from list
                category = edit["category"]
                item = edit["value"]
                
                # Remove item if list exists
                if category in self.user_model.current_user and isinstance(self.user_model.current_user[category], list):
                    if item in self.user_model.current_user[category]:
                        self.user_model.current_user[category].remove(item)
                        print(f"Removed '{item}' from {category}")
                        edits_processed = True
                        
                    # If list is now empty, remove the category
                    if not self.user_model.current_user[category]:
                        del self.user_model.current_user[category]
                        print(f"Removed empty category {category}")
        
        # Save changes to user model
        if edits_processed:
            self.user_model.save_current_user()
            llm_speak("Knowledge profile updated.")
    
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
            if self.test_mode:
                self.ui.set_status("TEST MODE - Initializing...", True)
            else:
                self.ui.set_status("Processing logs...", True)
            
        # Handle initial greeting and user identification
        self.handle_initial_greeting()
        
        # Print exit instructions
        self.ui.print_exit_instructions()
        
        # Reset status
        if hasattr(self.ui, 'set_status'):
            if self.test_mode:
                self.ui.set_status("TEST MODE - Ready")
            else:
                self.ui.set_status("Ready")
        
        # Main chat loop
        while True:
            # Get user input
            user_prefix = self.get_user_prefix()
            user_input = self.ui.get_user_input(user_prefix[:-1])  # Remove colon from prefix
            
            # Check for exit command
            if self.ui.handle_exit_command(user_input):
                exit_message = "Ending chat session. Goodbye!"
                llm_speak(exit_message)
                break
            
            # Check for specific keywords that might trigger intent recognition
            intent_triggered = False
            if self.intent_classifier and self.intent_vectorizer:
                if any(keyword in user_input.lower() for keyword in ["what time", "current time", "tell me the time", "play music"]):
                    predicted_intent = get_intent(user_input, self.intent_classifier, self.intent_vectorizer, threshold=0.65)
                    
                    if predicted_intent is not None and predicted_intent in intent_functions:
                        # Get the function from the map
                        command_func = intent_functions[predicted_intent]
                        
                        # For functions that need context
                        if predicted_intent == "shut_down":
                            core_prompt = self.load_system_prompt()
                            context = self.format_user_information()
                            response = command_func(core_prompt, context)
                        else:
                            response = command_func()
                            
                        # Display, speak, and log response
                        self.ui.print_jupiter_message(response)
                        llm_speak(response)
                        self.logger.log_message("Jupiter:", response)
                        
                        # Reset status if UI supports it
                        if hasattr(self.ui, 'set_status'):
                            if self.test_mode:
                                self.ui.set_status("TEST MODE - Ready")
                            else:
                                self.ui.set_status("Ready")
                                
                        intent_triggered = True
                
            # If an intent was triggered, skip to next loop iteration
            if intent_triggered:
                continue
            
            # Set busy status
            if hasattr(self.ui, 'set_status'):
                status_text = "Processing your request..."
                if self.test_mode:
                    status_text = "TEST MODE - " + status_text
                self.ui.set_status(status_text, True)
            
            # Check for user commands
            command_response = self.handle_user_commands(user_input)
            if command_response:
                self.ui.print_jupiter_message(command_response)
                self.logger.log_message("Jupiter:", command_response)
                
                # Reset status
                if hasattr(self.ui, 'set_status'):
                    if self.test_mode:
                        self.ui.set_status("TEST MODE - Ready")
                    else:
                        self.ui.set_status("Ready")
                    
                continue
            
            # Log user message
            self.logger.log_message(user_prefix, user_input)
            
            # Add user input to history
            self.conversation_history.append(f"{user_prefix} {user_input}")
            
            # Update status to show Jupiter is generating a response
            if hasattr(self.ui, 'set_status'):
                status_text = "Thinking..."
                if self.test_mode:
                    status_text = "TEST MODE - " + status_text
                self.ui.set_status(status_text, True)
            
            # Prepare and send to LLM
            llm_message = self.prepare_message_for_llm(user_input)
            response = self.llm_client.generate_chat_response(
                llm_message, 
                temperature=self.config['llm']['chat_temperature']
            )
            
            # Print and log response
            self.ui.print_jupiter_message(response)
            self.logger.log_message("Jupiter:", response)
            
            # Speak the response directly
            llm_speak(response)
            
            # Add response to history
            self.conversation_history.append(f"Jupiter: {response}")
            
            # Reset status
            if hasattr(self.ui, 'set_status'):
                if self.test_mode:
                    self.ui.set_status("TEST MODE - Ready")
                else:
                    self.ui.set_status("Ready")