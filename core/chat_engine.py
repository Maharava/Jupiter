import os
import json
import datetime
import threading
import re
import logging

# Fix the incorrect import path - remove circular dependency
try:
    # Import the command registry instead
    from utils.commands.registry import registry
except ImportError:
    print("Could not import command registry, commands may not work correctly")
    registry = None

from utils.intent_recog import load_model, get_intent
from utils.voice_cmd import intent_functions
from utils.text_processing import count_tokens
from utils.memory.conversation_manager import ConversationManager
from utils.voice_manager import VoiceManager, VoiceState
from utils.piper import llm_speak
from utils.llm_exchange_logger import LLMExchangeLogger

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
        
        # Set current platform - use terminal instead of GUI
        self.current_platform = "terminal"
        
        # Initialize conversation manager (replaces conversation_history)
        self.conversation_manager = ConversationManager(config, user_data_manager)
        
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
        
        # Initialize LLM exchange logger
        self.exchange_logger = LLMExchangeLogger(config['paths']['logs_folder'])
        
        if self.test_mode:
            print(f"🧪 ChatEngine initialized in TEST MODE")
        
        # Get current persona
        from utils.config import get_current_persona
        self.persona = get_current_persona(config)
        self.ai_name = self.persona["name"]
        
        # Update UI with persona
        if hasattr(self.ui, "set_ai_name"):
            self.ui.set_ai_name(self.ai_name)
    
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
    
    def load_system_prompt(self):
        """Load system prompt from file"""
        system_prompt_path = os.path.join(self.config['paths']['prompt_folder'], "system_prompt.txt")
        if (os.path.exists(system_prompt_path)):
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
            if category in ['user_id', 'created_at', 'last_seen', 'platforms', 'conversations']:
                continue
                
            # Format lists (likes, dislikes, etc.)
            if isinstance(value, list) and value:
                formatted_info += f"- {category.capitalize()}: {', '.join(value)}\n"
            # Format simple key-value pairs
            elif value and not isinstance(value, list) and not isinstance(value, dict):
                formatted_info += f"- {category.capitalize()}: {value}\n"
        
        return formatted_info
    
    def prepare_message_for_llm(self, user_input):
        """Prepare complete message for LLM with history and prompt using conversation manager"""
        # Load and enhance system prompt
        system_prompt = self.load_system_prompt()
        user_info = self.format_user_information()
        enhanced_system_prompt = system_prompt + user_info
        
        # Use conversation manager to prepare the message with appropriate context
        return self.conversation_manager.prepare_for_llm(
            user_input,
            enhanced_system_prompt,
            self.config['llm']['token_limit']
        )
    
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
        if hasattr(self.ui, 'is_terminal') and self.ui.is_terminal:
            # Skip command processing for non-command inputs in terminal mode
            if not user_input.startswith('/'):
                return None
        
        # Command mapping for cleaner handling
        command_handlers = {
            '/voice': self._handle_voice_command,
            '/name': self._handle_name_command,
            '/memory': self._handle_memory_command,
            '/debug voice': self._handle_debug_voice_command,
            '/help': self._handle_help_command,
            '/history': self._handle_history_command,
            '/conversation': self._handle_conversation_command,
            '/search': self._handle_search_command
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
            if cmd_prefix.startswith(command):
                return handler(args)
        
        # Lazy import the registry only when needed
        # This helps avoid circular dependencies
        try:
            from utils.commands.registry import registry
            
            # Strip the leading slash for registry lookup
            cmd_name = command[1:] if command.startswith('/') else command
            
            # Look for command in registry
            cmd = registry.get_command(cmd_name)
            if cmd and (self.current_platform in cmd.platforms or not cmd.platforms):
                # Prepare context object similar to what command handlers expect
                ctx = {
                    "platform": self.current_platform,  # This is now always "terminal"
                    "user": self.user_data_manager.current_user,
                    "ui": self.ui,
                    "user_manager": self.user_data_manager,
                    "llm_client": self.llm_client,
                    "client": getattr(self, "client", None),
                    "conversation_manager": self.conversation_manager
                }
                
                # Execute the command handler
                try:
                    return cmd.handler(ctx, args)
                except Exception as e:
                    # Fix the logging error by using standard logging
                    import logging
                    logging.error(f"Error executing command '{cmd_name}': {e}")
                    return f"Error executing command: {str(e)}"
        except ImportError:
            logger.error("Could not import command registry, commands may not work correctly")
                
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
        # Lazy import the registry only when needed
        try:
            from utils.commands.registry import registry
            
            commands = registry.get_for_platform(self.current_platform)
            
            help_text = "# Available Commands\n\n"
            
            # Group commands by category
            for cmd in sorted(commands, key=lambda x: x.name):
                help_text += f"- `{cmd.usage}` - {cmd.description}\n"
            
            # Add built-in commands not in registry
            help_text += "\n## Additional Commands\n"
            help_text += "- `/voice on|off` - Enable or disable voice recognition\n"
            help_text += "- `/memory` - Show what I remember about you\n"
            help_text += "- `/history [limit|with username]` - Show conversation history\n"
            help_text += "- `/conversation [ID|current]` - View a specific conversation\n"
            help_text += "- `/search [query]` - Search your conversations\n"
            
            # Add test mode info
            if self.test_mode:
                help_text += "\n⚠️ TEST MODE is active - running without LLM backend\n"
            
            self._speak_response("Here are the available commands.")
            return help_text
        except ImportError:
            return "Could not load command registry. Basic commands are still available."
    
    def _handle_history_command(self, args):
        """
        Handle /history command to display conversation history
        
        Arguments:
            args: Command arguments - can be a number to limit results
                  or "with [username]" to find shared conversations
        
        Returns:
            Formatted history display
        """
        # Parse arguments
        try:
            if args and args.isdigit():
                limit = int(args)
            elif args and args.lower().startswith("with "):
                # Handle "with [username]" format to find shared conversations
                other_username = args[5:].strip()
                return self._get_shared_history(other_username)
            else:
                limit = 10  # Default limit
        except ValueError:
            limit = 10
        
        # Get current user ID
        user_id = self.user_data_manager.current_user.get('user_id')
        if not user_id:
            return "You need to be logged in to view conversation history."
        
        # Get conversations
        conversations = self.conversation_manager.get_user_conversations(user_id, limit)
        
        if not conversations:
            return "You don't have any saved conversations yet."
        
        # Format output
        result = f"## Your Recent Conversations (Last {len(conversations)})\n\n"
        
        for i, conv in enumerate(conversations, 1):
            # Format date
            date_str = datetime.datetime.fromtimestamp(conv["created_at"]).strftime("%Y-%m-%d %H:%M")
            
            # Get participant names
            participant_names = []
            for p_id in conv["participants"]:
                if p_id == user_id:
                    continue  # Skip current user
                user = self.user_data_manager.get_user_by_id(p_id)
                if user:
                    participant_names.append(user.get("name", "Unknown"))
            
            # Format participants
            with_users = ""
            if participant_names:
                with_users = f" with {', '.join(participant_names)}"
            
            # Add to result
            result += f"{i}. **{conv['title']}**\n"
            result += f"   - Date: {date_str}{with_users}\n"
            result += f"   - Messages: {conv['message_count']}\n"
            result += f"   - ID: `{conv['conversation_id']}`\n\n"
        
        result += "Use `/conversation [ID]` to view a specific conversation."
        return result

    def _get_shared_history(self, other_username):
        """Find conversations shared with another user"""
        # Get current user ID
        current_user_id = self.user_data_manager.current_user.get('user_id')
        if not current_user_id:
            return "You need to be logged in to view shared conversations."
        
        # Find the other user
        other_user = self.user_data_manager.find_user_by_name(other_username)
        if not other_user:
            return f"Could not find a user named '{other_username}'."
        
        other_user_id = other_user.get('user_id')
        
        # Get shared conversations
        shared_convs = self.conversation_manager.get_shared_conversations([current_user_id, other_user_id])
        
        if not shared_convs:
            return f"You don't have any conversations with {other_username}."
        
        # Format output
        result = f"## Conversations with {other_username}\n\n"
        
        for i, conv in enumerate(shared_convs, 1):
            # Format date
            date_str = datetime.datetime.fromtimestamp(conv["created_at"]).strftime("%Y-%m-%d %H:%M")
            
            # Add to result
            result += f"{i}. **{conv['title']}**\n"
            result += f"   - Date: {date_str}\n"
            result += f"   - Messages: {conv['message_count']}\n"
            result += f"   - ID: `{conv['conversation_id']}`\n\n"
        
        result += "Use `/conversation [ID]` to view a specific conversation."
        return result

    def _handle_conversation_command(self, args):
        """
        Handle /conversation command to view a specific conversation
        
        Arguments:
            args: Command arguments - can be 'current' or a conversation ID
            
        Returns:
            Formatted conversation display
        """
        # Parse arguments
        if not args:
            return "Please specify a conversation ID or 'current' to view the current conversation."
        
        # Handle 'current' shortcut
        if args.lower() == 'current':
            conversation_id = self.conversation_manager.current_conversation_id
            if not conversation_id:
                return "No active conversation found."
        else:
            # Use the provided ID
            conversation_id = args.strip()
        
        # Get the conversation
        conversation = self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            return f"Conversation with ID '{conversation_id}' not found."
        
        # Format the conversation
        messages = conversation.get("messages", [])
        if not messages:
            return f"Conversation '{conversation['title']}' exists but has no messages."
        
        # Format date
        date_str = datetime.datetime.fromtimestamp(conversation["created_at"]).strftime("%Y-%m-%d %H:%M")
        
        # Get participant names
        participant_names = []
        for p_id in conversation["participants"]:
            user = self.user_data_manager.get_user_by_id(p_id)
            if user:
                participant_names.append(user.get("name", "Unknown"))
        
        # Format output
        result = f"# {conversation['title']}\n"
        result += f"Date: {date_str}\n"
        result += f"Participants: {', '.join(participant_names)}\n\n"
        
        # Add messages
        for msg in messages:
            sender_id = msg.get("sender_id", "unknown")
            content = msg.get("content", "")
            
            if sender_id == "jupiter":
                sender_name = "Jupiter"
            else:
                user = self.user_data_manager.get_user_by_id(sender_id)
                sender_name = user.get("name", "Unknown") if user else "Unknown"
            
            result += f"**{sender_name}**: {content}\n\n"
        
        return result

    def _handle_search_command(self, args):
        """
        Handle /search command to search conversations
        
        Arguments:
            args: Search query string
            
        Returns:
            Formatted search results
        """
        if not args:
            return "Please provide a search query after the /search command."
        
        # Get current user ID
        user_id = self.user_data_manager.current_user.get('user_id')
        if not user_id:
            return "You need to be logged in to search your conversations."
        
        # Search conversations
        results = self.conversation_manager.search_conversations(user_id, args)
        
        if not results:
            return f"No results found for '{args}'."
        
        # Format output
        output = f"# Search Results for '{args}'\n\n"
        
        for i, result in enumerate(results, 1):
            date_str = datetime.datetime.fromtimestamp(result["created_at"]).strftime("%Y-%m-%d %H:%M")
            output += f"{i}. **{result['title']}** ({date_str})\n"
            output += f"   - {len(result['matches'])} matching messages\n"
            output += f"   - ID: `{result['conversation_id']}`\n\n"
            
            # Show sample matches (limited to first 3)
            output += "**Sample matches:**\n"
            for j, message in enumerate(result['matches'][:3], 1):
                sender_id = message.get("sender_id", "unknown")
                if sender_id == "jupiter":
                    sender_name = "Jupiter"
                else:
                    user = self.user_data_manager.get_user_by_id(sender_id)
                    sender_name = user.get("name", "Unknown") if user else "Unknown"
                    
                content = message.get("content", "")
                
                # Truncate very long messages
                if len(content) > 100:
                    content = content[:97] + "..."
                    
                output += f"{j}. **{sender_name}**: {content}\n"
            
            output += "\n"
        
        output += "Use `/conversation [ID]` to view a specific conversation."
        return output

    def __del__(self):
        """Clean up when the object is destroyed"""
        try:
            # Clean up voice manager
            if hasattr(self, 'voice_manager') and self.voice_manager:
                self.voice_manager.stop()
        except:
            pass
        
        # Clean up all exchange sessions
        if hasattr(self, 'exchange_logger'):
            self.exchange_logger.cleanup_all_sessions(delete_logs=False)
            
    def restart_chat(self):
        """Restart chat session while preserving user data"""
        # Log that we're restarting
        self.logger.log_message("System:", "Chat session restarted by user")
        
        # Start a new log file
        self.logger.start_new_log()
        
        # Start a new conversation with conversation manager
        user_id = self.user_data_manager.current_user.get('user_id')
        if user_id:
            self.conversation_manager.start_conversation([user_id])
        
        # Special test mode notice if applicable
        test_mode_notice = ""
        if self.test_mode:
            test_mode_notice = " (TEST MODE ACTIVE)"
        
        # Show welcome message
        restart_message = f"=== {self.ai_name} Chat Restarted{test_mode_notice} ==="
        self.ui.print_jupiter_message(restart_message)
        
        greeting = f"Hello again, {self.user_data_manager.current_user.get('name', 'User')}! How can I help you today?"
        self.ui.print_jupiter_message(greeting)
        self._speak_response(greeting)
    
    def run(self):
        """Run the chat interface"""
        # Setup phase
        self.ui.print_welcome()
        self._setup_ui_callbacks()
        self.handle_initial_greeting()
        self.ui.print_exit_instructions()
        self._initialize_voice_features()
        
        # Main chat loop
        while True:
            # Get user input
            user_prefix = self.get_user_prefix()
            user_input = self.ui.get_user_input(user_prefix[:-1])
            
            # Check for exit
            if self.ui.handle_exit_command(user_input):
                self._speak_response("Ending chat session. Goodbye!")
                # End logging session and delete logs
                user_id = self.user_data_manager.current_user.get('user_id')
                if user_id:
                    self.exchange_logger.end_session(user_id, delete_logs=False)
                break
                
            # Log user input
            self.logger.log_message(user_prefix, user_input)
            
            # Check for intent triggers
            if self._process_intent(user_input):
                continue
            
            # Check for commands
            command_response = self.handle_user_commands(user_input)
            if command_response:
                self.ui.print_jupiter_message(command_response)
                self.logger.log_message("Jupiter:", command_response)
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
        
        # Start a new conversation with this user
        user_id = user_data.get('user_id')
        if user_id:
            self.conversation_manager.start_conversation([user_id])
        
        # Start exchange logging for this user
        if user_id:
            self.exchange_logger.start_session(user_id, actual_name)
        
        # Check if this is a returning user
        if actual_name.lower() == name.lower() and actual_name != name:
            # This is a returning user with different capitalization
            welcome = f"Welcome back, {actual_name}! It's great to chat with you again."
            if self.test_mode:
                welcome += " (TEST MODE ACTIVE)"
            
            self.ui.print_jupiter_message(welcome)
            self._speak_response(f"Welcome back, {actual_name}! It's great to chat with you again.")
            
            # Save greeting to conversation
            self.conversation_manager.add_to_context("jupiter", welcome, "assistant")
            
        elif 'likes' in user_data or 'interests' in user_data:
            # This is a returning user with known preferences
            welcome = f"Welcome back, {actual_name}! It's great to chat with you again."
            if self.test_mode:
                welcome += " (TEST MODE ACTIVE)"
            
            self.ui.print_jupiter_message(welcome)
            self._speak_response(f"Welcome back, {actual_name}! It's great to chat with you again.")
            
            # Save greeting to conversation
            self.conversation_manager.add_to_context("jupiter", welcome, "assistant")
            
        else:
            # New user or user without preferences
            greeting = f"Nice to meet you, {name}! How can I help you today?"
            if self.test_mode:
                greeting += " (TEST MODE ACTIVE)"
            
            self.ui.print_jupiter_message(greeting)
            self._speak_response(f"Nice to meet you, {name}! How can I help you today?")
            
            # Save greeting to conversation
            self.conversation_manager.add_to_context("jupiter", greeting, "assistant")
            
        # User is now logged in - trigger callbacks
        self._user_logged_in()
    
    def _process_and_respond(self, user_input, user_prefix):
        """Process user input and generate response using conversation manager"""
        # Get current user ID
        user_id = self.user_data_manager.current_user.get('user_id', 'unknown')
        
        # Add to conversation context
        self.conversation_manager.add_to_context(user_id, user_input, "user")
        
        # Generate response
        llm_message = self.prepare_message_for_llm(user_input)
        response = self.llm_client.generate_chat_response(
            llm_message, 
            temperature=self.config['llm']['chat_temperature']
        )
        
        # Validate and clean the response
        response = self._validate_response(response)
        
        # If response is empty after validation, retry with modified prompt
        retry_count = 0
        max_retries = 2
        
        while not response.strip() and retry_count < max_retries:
            self.logger.warning(f"Empty response detected, retrying ({retry_count+1}/{max_retries})")
            
            # Modify the prompt to instruct LLM to avoid user names
            retry_message = llm_message + "\n\nIMPORTANT: Your previous response was filtered. A response MUST be provided without mentioning yours or the user's names."
            
            # Try again with modified prompt
            response = self.llm_client.generate_chat_response(
                retry_message,
                temperature=self.config['llm']['chat_temperature'] * 0.9  # Slightly reduce temperature
            )
            
            # Validate again
            response = self._validate_response(response)
            retry_count += 1
        
        # If still empty, provide a fallback message
        if not response.strip():
            response = "I apologize, but I'm having trouble generating an appropriate response. Could you please rephrase your question or ask something else?"
        
        # Log the complete exchange
        self.exchange_logger.log_exchange(user_id, llm_message, user_input, response)
        
        # Output response
        self.ui.print_jupiter_message(response)
        self.logger.log_message("Jupiter:", response)
        self._speak_response(response)
        
        # Add to conversation context
        self.conversation_manager.add_to_context(self.ai_name.lower(), response, "assistant")
        
        return response
    
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
                lambda state: None  # No UI callbacks needed in terminal mode
            )

    def _initialize_voice_features(self):
        """Initialize and start voice features if available"""
        if hasattr(self, 'voice_manager') and self.voice_manager:
            try:
                # Start the voice manager if it exists and isn't already running
                if not self.voice_manager.running:
                    self.voice_manager.start()
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

    def _validate_response(self, response):
        """Ensure the response doesn't contain simulated user dialogue"""
        # Get user name and prepare variations for detection
        user_name = self.user_data_manager.current_user.get('name', 'User')
        
        # Create patterns with name variations (standard, lowercase, uppercase)
        patterns = [
            f"{user_name}:",  # Standard: Hannah:
            f"{user_name.lower()}:",  # Lowercase: hannah:
            f"\n{user_name}:",  # Newline before: \nHannah:
            f"\n{user_name.lower()}:",  # Lowercase with newline: \nhannah:
            f"\n{user_name} ",  # Name at start of line: \nHannah says
            f"\n{user_name.lower()} ",  # Lowercase at start: \nhannah says
            f"\n{user_name} says",  # Common dialogue format
            f"\n{user_name} asked",  # Another dialogue format
            "User:",  # Generic user marker
            "\nYou:"   # AI referring to user as "You"
        ]
        
        # If any pattern is found, truncate the response at that point
        for pattern in patterns:
            if pattern in response:
                # Truncate at the first occurrence
                truncated = response.split(pattern)[0].strip()
                logger.warning(f"Detected AI speaking for user '{pattern}', truncating response")
                return truncated
        
        return response

    def get_user_conversations(self, limit=10):
        """Get the current user's conversation history"""
        user_id = self.user_data_manager.current_user.get('user_id')
        if user_id:
            return self.conversation_manager.get_user_conversations(user_id, limit)
        return []
    
    def search_conversations(self, query):
        """Search the current user's conversations"""
        user_id = self.user_data_manager.current_user.get('user_id')
        if user_id:
            return self.conversation_manager.search_conversations(user_id, query)
        return []