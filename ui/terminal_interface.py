from colorama import init, Fore, Style
import sys

class TerminalInterface:
    """Manages terminal UI for Jupiter Chat"""
    
    def __init__(self, jupiter_color="yellow", user_color="magenta"):
        """Initialize terminal interface with colors"""
        # Initialize colorama
        init()
        
        # Set colors
        self.JUPITER_COLOR = getattr(Fore, jupiter_color.upper())
        self.USER_COLOR = getattr(Fore, user_color.upper())
        self.SYSTEM_COLOR = Fore.CYAN
        self.Style = Style
        
        # Current status
        self.current_status = "Ready"
        
        # User prefix
        self.user_prefix = "User"
        
        # Add available colors
        self.colors = {
            "black", "red", "green", "yellow", "blue", 
            "magenta", "cyan", "white", "purple", "orange"
        }
    
    def print_jupiter_message(self, message):
        """Print a message from Jupiter with correct color"""
        print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} {message}")
        
    def display_status_bubble(self, text):
        """Display a status bubble for voice interactions in terminal"""
        print(f"\n[Voice] {text}\n")
        
    def remove_status_bubble(self):
        """Remove the status bubble (does nothing in terminal)"""
        pass
        
    def update_voice_state(self, state):
        """Update the UI based on voice state changes (minimal for terminal)"""
        # No visual indicator in terminal mode
        pass
        
    def setup_voice_indicator(self, toggle_callback):
        """Set up voice indicator with toggle callback (does nothing in terminal)"""
        # No visual indicator to set up in terminal mode
        pass
    
    def get_user_input(self, prefix="User"):
        """Get input from user with correct color"""
        # Update stored prefix (remove colon if present)
        self.user_prefix = prefix.rstrip(':')
        
        # Show prompt and get input
        return input(f"{self.USER_COLOR}{prefix}:{self.Style.RESET_ALL} ")
    
    def print_welcome(self):
        """Print welcome message"""
        print("=== Jupiter Chat ===")
    
    def print_exit_instructions(self):
        """Print exit instructions"""
        print("Type 'exit' or 'quit' to end the conversation.")
    
    def handle_exit_command(self, user_input):
        """Check if user wants to exit"""
        if user_input.lower() in ['exit', 'quit']:
            self.print_jupiter_message("Ending chat session. Goodbye!")
            return True
        return False
    
    def exit_program(self):
        """Exit the program"""
        sys.exit(0)
    
    def set_status(self, status_text, is_busy=False):
        """Set status message (primarily for compatibility with GUI)"""
        self.current_status = status_text
        
        # For terminal, we'll print status changes only for certain conditions
        if is_busy and status_text != "Ready":
            print(f"{self.SYSTEM_COLOR}[{status_text}]{self.Style.RESET_ALL}")
    
    def clear_chat(self):
        """Clear chat (not supported in terminal mode)"""
        # Not supported in terminal mode, but added for compatibility
        print(f"{self.SYSTEM_COLOR}[Chat cleared]{self.Style.RESET_ALL}")
    
    def display_status_bubble(self, text):
        """Display a status bubble for speech (terminal version)"""
        print(f"{self.SYSTEM_COLOR}[🎤 {text}]{self.Style.RESET_ALL}")
    
    def remove_status_bubble(self):
        """Remove status bubble (not needed in terminal mode)"""
        # No-op in terminal mode, added for compatibility
        pass
    
    def update_voice_state(self, state):
        """Update voice state indicator (terminal version)"""
        if state:
            state_name = state.name if hasattr(state, "name") else str(state)
            print(f"{self.SYSTEM_COLOR}[Voice: {state_name}]{self.Style.RESET_ALL}")
    
    def setup_voice_indicator(self, toggle_callback=None):
        """Setup voice indicator (not applicable for terminal)"""
        # No-op in terminal mode, added for compatibility
        pass

    def prompt_for_input(self, prompt=None):
        """Prompt the user for input, optionally with a custom prompt"""
        if prompt:
            print(f"\n{prompt}")
        # Print the standard input prompt
        print(f"{self.user_prefix}", end="", flush=True)

    def set_ai_name(self, name):
        """Set the AI assistant's name"""
        self.ai_name = name
        self.jupiter_prefix = f"{self.ai_name}: "

    def set_ai_color(self, color):
        """Set the AI assistant's color"""
        if color in self.colors:
            self.jupiter_color = color
        else:
            print(f"Warning: Color '{color}' not available, using default '{self.jupiter_color}'")