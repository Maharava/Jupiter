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
        self.Style = Style
    
    def print_jupiter_message(self, message):
        """Print a message from Jupiter with correct color"""
        print(f"{self.JUPITER_COLOR}Jupiter:{self.Style.RESET_ALL} {message}")
    
    def get_user_input(self, prefix="User"):
        """Get input from user with correct color"""
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