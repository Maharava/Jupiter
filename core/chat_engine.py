import os
import json
import datetime
import threading
import re
import logging

from user_id_commands import handle_id_commands
from utils.intent_recog import load_model, get_intent
from utils.voice_cmd import intent_functions
from utils.text_processing import count_tokens, truncate_to_token_limit
from utils.voice_manager import VoiceManager, VoiceState
from utils.piper import llm_speak

# Set up logging
logger = logging.getLogger("jupiter.core.chat_engine")

class ChatEngine:
    """Core chat functionality for Jupiter"""
    
    def __init__(self, llm_client, user_data_manager, logger, ui, config, test_mode=False):
        """Initialize chat engine with dependencies"""
        self.llm_client = llm_client
        self.user_data_manager = user_data_manager
        self.logger = logger
        self.ui = ui
        self.config = config
        self.test_mode = test_mode
        
        # Initialize conversation history with a maximum size
        self.conversation_history = []
        self.max_history_messages = config.get('chat', {}).get('max_history_messages', 100)
        
        # Create necessary folders
        os.makedirs(config['paths']['prompt_folder'], exist_ok=True)
        os.makedirs(config['paths']['logs_folder'], exist_ok=True)
        
        # Load intent recognition model
        try:
            self.intent_classifier, self.intent_vectorizer = load_model()
        except Exception as e:
            logger.error(f"Failed to load intent model: {e}")
            print(f"Failed to load intent model: {e}")
            self.intent_classifier = None
            self.intent_vectorizer = None
        
        # Initialize voice manager
        self.voice_manager = self._initialize_voice_manager()
        
        if self.test_mode:
            print(f"🧪 ChatEngine initialized in TEST MODE")
        
        # Get current persona
        from utils.config import get_current_persona
        self.persona = get_current_persona(config)
        self.ai_name = self.persona["name"]
        
        # Update UI with persona
        if hasattr(self.ui, "set_ai_name"):
            self.ui.set_ai_name(self.ai_name)
            
        if hasattr(self.ui, "set_ai_color") and "color" in self.persona:
            try:
                self.ui.set_ai_color(self.persona["color"])
            except Exception as e:
                self.logger.warning(f"Could not set AI color: {e}")
    
    def _initialize_voice_manager(self):
        """Initialize simplified voice manager for TTS only"""
        try:
            # Get voice enabled setting from config
            voice_enabled = self.config.get('voice', {}).get('enabled', True)
            
            # Create voice manager
            manager = VoiceManager(
                chat_engine=self,
                ui=self.ui,
                enabled=voice_enabled and not self.test_mode  # Disable in test mode
            )
            
            # Log success
            logger.info("Voice manager initialized for TTS only")
            
            return manager
                
        except Exception as e:
            logger.error(f"Failed to initialize voice manager: {e}", exc_info=True)
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status(f"Voice initialization error: {str(e)[:50]}", False)
            return None        
                
        # If we get here, model not found
        return None
    
    def _speak_response(self, text):
        """Convert text to speech with proper state management"""
        if self.voice_manager and self.voice_manager.enabled:
            # Use voice manager if available - with proper state transitions
            self.voice_manager.speak(text)
        else:
            # Direct fallback only if voice manager unavailable
            try:
                llm_speak(text)
            except Exception as e:
                logger.error(f"Error in text-to-speech: {e}")
    
    def add_to_conversation_history(self, message):
        """Add a message to conversation history with size management"""
        self.conversation_history.append(message)
        
        # Trim history if it exceeds maximum size
        if len(self.conversation_history) > self.max_history_messages:
            excess = len(self.conversation_history) - self.max_history_messages
            self.conversation_history = self.conversation_history[excess:]
    
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
            
            # Create directory if needed
            os.makedirs(os.path.dirname(system_prompt_path), exist_ok=True)
            
            with open(system_prompt_path, 'w', encoding='utf-8') as f:
                f.write(default_prompt)
            return default_prompt
    
    def format_user_information(self):
        """Format user information for inclusion in system prompt"""
        user_info = self.user_data_manager.current_user
        
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
                
            # Skip system fields
            if category in ['user_id', 'created_at', 'last_seen', 'platforms']:
                continue
                
            # Format lists (likes, dislikes, etc.)
            if isinstance(value, list) and value:
                formatted_info += f"- {category.capitalize()}: {', '.join(value)}\n"
            # Format simple key-value pairs
            elif value and not isinstance(value, list) and not isinstance(value, dict):
                formatted_info += f"- {category.capitalize()}: {value}\n"
        
        return formatted_info
    
    def prepare_message_for_llm(self, user_input):
        """Prepare complete message for LLM with history and prompt"""
        system_prompt = self.load_system_prompt()
        
        # Add user information to system prompt
        user_info = self.format_user_information()
        enhanced_system_prompt = system_prompt + user_info
        
        user_prefix = f"{self.user_data_manager.current_user.get('name', 'User')}:"
        
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
        return f"{self.user_data_manager.current_user.get('name', 'User')}:"
    
    def format_memory_display(self):
        """Format user memory information for display"""
        user_info = self.user_data_manager.current_user
        
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
        processed_keys = set(['user_id', 'created_at', 'last_seen', 'platforms'])  # Skip system fields
        
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
        """Handle user commands with voice system integration"""
        # Track platform (unchanged)
        self.current_platform = "gui"
        if hasattr(self.ui, 'is_terminal') and self.ui.is_terminal:
            self.current_platform = "terminal"
            
        # Command mapping for cleaner handling
        command_handlers = {
            '/voice': self._handle_voice_command,
            '/name': self._handle_name_command,
            '/memory': self._handle_memory_command,
            '/debug voice': self._handle_debug_voice_command,
            '/help': self._handle_help_command
        }
        
        # Extract command and arguments
        parts = user_input.split(None, 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Check for exact command match
        if command in command_handlers:
            return command_handlers[command](args)
        
        # Check for prefix matches
        for cmd_prefix, handler in command_handlers.items():
            if user_input.startswith(cmd_prefix):
                return handler(args)
                
        # Handle ID-related commands separately
        id_response = handle_id_commands(self, user_input)
        if id_response:
            return id_response
                
        # Not a command
        return None
    
    def _handle_voice_command(self, args):
        """Handle voice command"""
        parts = args.split(None, 1)
        if len(parts) > 1:
            # Check for on/off parameter
            param = parts[1].lower()
            if param in ('on', 'enable', 'activate'):
                enabled = True
            elif param in ('off', 'disable', 'deactivate'):
                enabled = False
            else:
                return "Usage: /voice on|off - Enable or disable voice recognition"
        else:
            # Toggle current state
            enabled = None
            
        # Toggle voice manager if available
        if self.voice_manager:
            enabled = self.voice_manager.toggle_voice(enabled)
            return f"Voice recognition {'enabled' if enabled else 'disabled'}"
        else:
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status("Voice system not available", False)
            return "Voice recognition system is not available - check the log for details"
    
    def _handle_name_command(self, args):
        """Handle name command"""
        new_name = args.strip()
        if new_name:
            # Update user name
            self.user_data_manager.current_user['name'] = new_name
            self.user_data_manager.save_current_user()
            response = f"I'll call you {new_name} from now on."
            self._speak_response(response)
            return response
        else:
            response = "Please provide a name after the /name command."
            self._speak_response(response)
            return response
    
    def _handle_memory_command(self, args):
        """Handle memory command"""
        response = self.format_memory_display()
        self._speak_response("Here's what I remember about you.")
        return response
    
    def _handle_debug_voice_command(self, args):
        """Handle debug voice command"""
        if not self.voice_manager:
            return "Voice system not initialized. Check log for errors."
            
        debug_info = [
            "Voice System Debug Information:",
            f"- Current state: {self.voice_manager.state.name if hasattr(self.voice_manager.state, 'name') else 'Unknown'}",
            f"- Enabled: {self.voice_manager.enabled}",
            f"- Model path: {self.voice_manager.model_path or 'Not found'}",
            f"- Model exists: {os.path.exists(self.voice_manager.model_path) if self.voice_manager.model_path else False}",
            f"- Audio capture: {'Active' if hasattr(self.voice_manager, 'audio_capture') and self.voice_manager.audio_capture else 'Not active'}"
        ]
        
        return "\n".join(debug_info)
    
    def _handle_help_command(self, args):
        """Handle help command"""
        help_text = """
Available commands:
/voice on|off - Enable or disable voice recognition
/name [new name] - Change your name
/memory - Show what I remember about you
/id - Show your Jupiter ID information
/link [platform] [username] - Link your identity with another platform
/debug voice - Show voice system diagnostic information
/help - Show this help message
        """
        
        # Add test mode info
        if self.test_mode:
            help_text += "\n⚠️ TEST MODE is active - running without LLM backend\n"
        
        self._speak_response("Here are the available commands.")
        return help_text
    
    def __del__(self):
        """Clean up when the object is destroyed"""
        try:
            # Clean up voice manager
            if hasattr(self, 'voice_manager') and self.voice_manager:
                self.voice_manager.stop()
        except:
            pass
            
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
        
        greeting = f"Hello again, {self.user_data_manager.current_user.get('name', 'User')}! How can I help you today?"
        self.ui.print_jupiter_message(greeting)
        self._speak_response(greeting)
        
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
        user_info = self.user_data_manager.current_user
        
        # Send data to UI and show knowledge view
        self.ui.create_knowledge_bubbles(user_info)
        self.ui.show_knowledge_view()
        
        # Speak notification
        self._speak_response("Showing your knowledge profile.")
        
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
            try:
                edit = self.ui.knowledge_edit_queue.get()
                
                # Handle different edit types
                if edit["action"] == "edit":
                    # Update simple value
                    self.user_data_manager.current_user[edit["category"]] = edit["new_value"]
                    logger.info(f"Updated {edit['category']} from '{edit['old_value']}' to '{edit['new_value']}'")
                    edits_processed = True
                        
                elif edit["action"] == "remove":
                    # Remove category entirely
                    if edit["category"] in self.user_data_manager.current_user:
                        del self.user_data_manager.current_user[edit["category"]]
                        logger.info(f"Removed {edit['category']}")
                        edits_processed = True
                        
                elif edit["action"] == "add_list_item":
                    # Add item to list
                    category = edit["category"]
                    new_item = edit["value"]
                    
                    # Create list if it doesn't exist
                    if category not in self.user_data_manager.current_user:
                        self.user_data_manager.current_user[category] = []
                        
                    # Add item if it's not already in the list
                    if new_item not in self.user_data_manager.current_user[category]:
                        self.user_data_manager.current_user[category].append(new_item)
                        logger.info(f"Added '{new_item}' to {category}")
                        edits_processed = True
                        
                elif edit["action"] == "remove_list_item":
                    # Remove item from list
                    category = edit["category"]
                    item = edit["value"]
                    
                    # Remove item if list exists
                    if category in self.user_data_manager.current_user and isinstance(self.user_data_manager.current_user[category], list):
                        if item in self.user_data_manager.current_user[category]:
                            self.user_data_manager.current_user[category].remove(item)
                            logger.info(f"Removed '{item}' from {category}")
                            edits_processed = True
                            
                        # If list is now empty, remove the category
                        if not self.user_data_manager.current_user[category]:
                            del self.user_data_manager.current_user[category]
                            logger.info(f"Removed empty category {category}")
                
                # Mark the task as done
                self.ui.knowledge_edit_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing knowledge edit: {e}")
                try:
                    self.ui.knowledge_edit_queue.task_done()
                except:
                    pass
        
        # Save changes to user model
        if edits_processed:
            self.user_data_manager.save_current_user()
            self._speak_response("Knowledge profile updated.")
    
    def run(self):
        """Run the chat interface"""
        # Setup phase
        self.ui.print_welcome()
        self._setup_ui_callbacks()
        self._update_ui_status("Initializing...", True)
        self.handle_initial_greeting()
        self.ui.print_exit_instructions()
        self._update_ui_status("Ready")
        self._initialize_voice_features()
        
        # Main chat loop
        while True:
            # Get user input
            user_prefix = self.get_user_prefix()
            user_input = self.ui.get_user_input(user_prefix[:-1])
            
            # Check for exit
            if self.ui.handle_exit_command(user_input):
                self._speak_response("Ending chat session. Goodbye!")
                break
                
            # Log user input
            self.logger.log_message(user_prefix, user_input)
            
            # Check for intent triggers
            if self._process_intent(user_input):
                continue
                
            # Update UI status
            self._update_ui_status("Processing your request...", True)
            
            # Check for commands
            command_response = self.handle_user_commands(user_input)
            if command_response:
                self.ui.print_jupiter_message(command_response)
                self.logger.log_message("Jupiter:", command_response)
                self._update_ui_status("Ready")
                continue
                
            # Process normal input
            self._process_and_respond(user_input, user_prefix)
    
    def handle_initial_greeting(self):
        """Handle initial greeting and user identification"""
        # Start a new log file
        self.logger.start_new_log()
        
        # Special test mode greeting if applicable
        test_mode_notice = ""
        if self.test_mode:
            test_mode_notice = " (TEST MODE - No LLM connection)"
        
        # Ask for name - use persona name instead of hardcoded "Jupiter"
        greeting = f"I'm {self.ai_name}{test_mode_notice}, your AI assistant. Please enter your name. Please ONLY type your name in. Consider it a username."
        self.ui.print_jupiter_message(greeting)
        self._speak_response(f"I'm {self.ai_name}, your AI assistant. Please enter your name.")
        
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
                self._speak_response(prompt)
        
        # Identify user and get user data
        user_data, actual_name = self.user_data_manager.identify_user(name)
        self.user_data_manager.set_current_user(user_data)
        
        # Check if this is a returning user
        if actual_name.lower() == name.lower() and actual_name != name:
            # This is a returning user with different capitalization
            welcome = f"Welcome back, {actual_name}! It's great to chat with you again."
            if self.test_mode:
                welcome += " (TEST MODE ACTIVE)"
            
            self.ui.print_jupiter_message(welcome)
            self._speak_response(f"Welcome back, {actual_name}! It's great to chat with you again.")
        elif 'likes' in user_data or 'interests' in user_data:
            # This is a returning user with known preferences
            welcome = f"Welcome back, {actual_name}! It's great to chat with you again."
            if self.test_mode:
                welcome += " (TEST MODE ACTIVE)"
            
            self.ui.print_jupiter_message(welcome)
            self._speak_response(f"Welcome back, {actual_name}! It's great to chat with you again.")
        else:
            # New user or user without preferences
            greeting = f"Nice to meet you, {name}! How can I help you today?"
            if self.test_mode:
                greeting += " (TEST MODE ACTIVE)"
            
            self.ui.print_jupiter_message(greeting)
            self._speak_response(f"Nice to meet you, {name}! How can I help you today?")
    
    def _process_and_respond(self, user_input, user_prefix):
        """Process user input and generate response"""
        # Add to history
        self.add_to_conversation_history(f"{user_prefix} {user_input}")
        
        # Update UI status
        self._update_ui_status("Thinking...", True)
        
        # Generate response
        llm_message = self.prepare_message_for_llm(user_input)
        response = self.llm_client.generate_chat_response(
            llm_message, 
            temperature=self.config['llm']['chat_temperature']
        )
        
        # Output response
        self.ui.print_jupiter_message(response)
        self.logger.log_message("Jupiter:", response)
        self._speak_response(response)
        
        # Add to history
        self.add_to_conversation_history(f"Jupiter: {response}")
        
        # Reset UI status
        self._update_ui_status("Ready")
        
        return response
    
    def _update_ui_status(self, message, busy=False):
        """Update UI status with test mode awareness"""
        if hasattr(self.ui, 'set_status'):
            status_text = message
            if self.test_mode:
                status_text = f"TEST MODE - {message}"
            self.ui.set_status(status_text, busy)
    
    def _process_intent(self, user_input):
        """Process input for intent recognition, returns True if handled"""
        if not (self.intent_classifier and self.intent_vectorizer):
            return False
            
        # Check for intent keywords
        intent_keywords = ["what time", "current time", "tell me the time", "play music"]
        if not any(keyword in user_input.lower() for keyword in intent_keywords):
            return False
            
        # Get predicted intent
        predicted_intent = get_intent(
            user_input, 
            self.intent_classifier, 
            self.intent_vectorizer, 
            threshold=0.65
        )
        
        # Check if we have a handler
        if predicted_intent is None or predicted_intent not in intent_functions:
            return False
            
        # Execute intent function
        command_func = intent_functions[predicted_intent]
        
        # Handle special cases
        if predicted_intent == "shut_down":
            core_prompt = self.load_system_prompt()
            context = self.format_user_information()
            response = command_func(core_prompt, context)
        else:
            response = command_func()
            
        # Output response
        self.ui.print_jupiter_message(response)
        self._speak_response(response)
        self.logger.log_message("Jupiter:", response)
        self._update_ui_status("Ready")
        
        return True

    def _setup_ui_callbacks(self):
        """Set up UI callbacks for voice features"""
        # Register the UI callback for voice state changes
        if hasattr(self, 'voice_manager') and self.voice_manager:
            self.voice_manager.set_ui_callback(
                lambda state: self.ui.update_voice_state(state) if hasattr(self.ui, 'update_voice_state') else None
            )

    def _initialize_voice_features(self):
        """Initialize and start voice features if available"""
        if hasattr(self, 'voice_manager') and self.voice_manager:
            try:
                # Start the voice manager if it exists and isn't already running
                if not self.voice_manager.running:
                    self.voice_manager.start()
                
                # Update UI if needed
                if hasattr(self.ui, 'set_status') and self.voice_manager.enabled:
                    if self.voice_manager.detector_available:
                        self.ui.set_status("Listening for wake word", False)
                    else:
                        self.ui.set_status("Voice active for speaking only", False)
            except Exception as e:
                logger.error(f"Error initializing voice features: {e}")

    def register_login_callback(self, callback):
        """Register a function to call after successful login"""
        self._login_callbacks = getattr(self, '_login_callbacks', [])
        self._login_callbacks.append(callback)
    
    def _user_logged_in(self):
        """Called when user successfully logs in"""
        callbacks = getattr(self, '_login_callbacks', [])
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Error in login callback: {e}")