import os
import sys
import unittest
import io
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter modules
from ui.terminal_interface import TerminalInterface

# Import test utilities
from test_utils.test_environment import setup_test_environment, cleanup_test_environment

class TestTerminalInterface(unittest.TestCase):
    """Test the Terminal User Interface"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        setup_test_environment()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up before each test"""
        # Create terminal interface with test colors
        self.ui = TerminalInterface(jupiter_color="blue", user_color="green")
    
    def test_initialization(self):
        """Test that the terminal interface initializes correctly"""
        # Check that colors are set correctly
        from colorama import Fore
        self.assertEqual(self.ui.JUPITER_COLOR, Fore.BLUE)
        self.assertEqual(self.ui.USER_COLOR, Fore.GREEN)
    
    @patch('builtins.print')
    def test_print_jupiter_message(self, mock_print):
        """Test printing a message from Jupiter"""
        # Print a test message
        self.ui.print_jupiter_message("Test message from Jupiter")
        
        # Check that print was called with the correct format
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        self.assertIn("Jupiter:", args)
        self.assertIn("Test message from Jupiter", args)
    
    @patch('builtins.input', return_value="Test input")
    def test_get_user_input(self, mock_input):
        """Test getting input from the user"""
        # Get user input
        result = self.ui.get_user_input()
        
        # Check that input was called and returned the correct value
        mock_input.assert_called_once()
        self.assertEqual(result, "Test input")
    
    @patch('builtins.input', return_value="Test input")
    def test_get_user_input_custom_prefix(self, mock_input):
        """Test getting input with a custom prefix"""
        # Get user input with custom prefix
        result = self.ui.get_user_input(prefix="CustomUser")
        
        # Check that input was called with the custom prefix
        mock_input.assert_called_once()
        args = mock_input.call_args[0][0]
        self.assertIn("CustomUser:", args)
        self.assertEqual(result, "Test input")
    
    @patch('builtins.print')
    def test_print_welcome(self, mock_print):
        """Test printing the welcome message"""
        # Print welcome message
        self.ui.print_welcome()
        
        # Check that print was called with the welcome message
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        self.assertIn("Jupiter Chat", args)
    
    @patch('builtins.print')
    def test_print_exit_instructions(self, mock_print):
        """Test printing exit instructions"""
        # Print exit instructions
        self.ui.print_exit_instructions()
        
        # Check that print was called with the exit instructions
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        self.assertIn("exit", args.lower())
        self.assertIn("quit", args.lower())
    
    def test_handle_exit_command(self):
        """Test handling exit commands"""
        # Test with exit command
        self.assertTrue(self.ui.handle_exit_command("exit"))
        self.assertTrue(self.ui.handle_exit_command("EXIT"))
        self.assertTrue(self.ui.handle_exit_command("Exit"))
        
        # Test with quit command
        self.assertTrue(self.ui.handle_exit_command("quit"))
        self.assertTrue(self.ui.handle_exit_command("QUIT"))
        self.assertTrue(self.ui.handle_exit_command("Quit"))
        
        # Test with other commands
        self.assertFalse(self.ui.handle_exit_command("hello"))
        self.assertFalse(self.ui.handle_exit_command("help"))
        self.assertFalse(self.ui.handle_exit_command(""))
    
    @patch('sys.exit')
    def test_exit_program(self, mock_exit):
        """Test exiting the program"""
        # Exit the program
        self.ui.exit_program()
        
        # Check that sys.exit was called
        mock_exit.assert_called_once_with(0)
    
    @patch('builtins.print')
    @patch('builtins.input', side_effect=["hello", "exit"])
    def test_full_conversation_flow(self, mock_input, mock_print):
        """Test a full conversation flow"""
        # Simulate a conversation
        self.ui.print_welcome()
        
        user_input = self.ui.get_user_input()
        self.assertEqual(user_input, "hello")
        
        self.ui.print_jupiter_message("Hello! How can I help you today?")
        
        user_input = self.ui.get_user_input()
        self.assertEqual(user_input, "exit")
        
        exit_detected = self.ui.handle_exit_command(user_input)
        self.assertTrue(exit_detected)
        
        self.ui.print_jupiter_message("Goodbye!")
        
        # Check that print was called the expected number of times
        self.assertEqual(mock_print.call_count, 3)  # Welcome, Jupiter response, Goodbye
    
    @patch('builtins.print')
    def test_color_formatting(self, mock_print):
        """Test that color formatting is applied correctly"""
        from colorama import Fore, Style
        
        # Print messages
        self.ui.print_jupiter_message("Test message")
        
        # Check that color codes are included in the output
        calls = mock_print.call_args_list
        self.assertEqual(len(calls), 1)
        
        args = calls[0][0][0]
        self.assertIn(Fore.BLUE, args)  # Jupiter color
        self.assertIn(Style.RESET_ALL, args)  # Reset color
    
    @patch('builtins.print')
    def test_custom_colors(self, mock_print):
        """Test using custom colors"""
        from colorama import Fore, Style
        
        # Create UI with custom colors
        custom_ui = TerminalInterface(jupiter_color="red", user_color="yellow")
        
        # Print messages
        custom_ui.print_jupiter_message("Test message")
        
        # Check that custom color codes are used
        calls = mock_print.call_args_list
        self.assertEqual(len(calls), 1)
        
        args = calls[0][0][0]
        self.assertIn(Fore.RED, args)  # Custom Jupiter color
        self.assertIn(Style.RESET_ALL, args)  # Reset color
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_error_handling(self, mock_print, mock_input):
        """Test error handling during input"""
        # Simulate an input error
        mock_input.side_effect = EOFError("Input error")
        
        # This should handle the error gracefully
        with self.assertRaises(EOFError):
            self.ui.get_user_input()

if __name__ == '__main__':
    unittest.main()
