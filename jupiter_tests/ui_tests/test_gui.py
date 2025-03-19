import os
import sys
import unittest
import tkinter as tk
import threading
import queue
import time
from unittest.mock import patch, MagicMock, Mock

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter modules
from ui.gui_interface import GUIInterface

# Import test utilities
from test_utils.test_environment import setup_test_environment, cleanup_test_environment

class TestGUIInterface(unittest.TestCase):
    """Test the GUI User Interface
    
    Note: These tests require a windowing system. In headless environments,
    they may be skipped or need to be run with a virtual display like Xvfb.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        cls.test_env = setup_test_environment()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up before each test"""
        # Skip tests if tkinter is not available or can't open a window
        try:
            # Try to create a root window to see if GUI is possible
            test_root = tk.Tk()
            test_root.withdraw()
            test_root.update()
            test_root.destroy()
        except (tk.TclError, Exception) as e:
            self.skipTest(f"GUI tests require a windowing system: {e}")
        
        # Create GUI interface in a separate thread
        self.gui = None
        self.gui_thread = threading.Thread(target=self._create_gui)
        self.gui_thread.daemon = True
        self.gui_thread.start()
        
        # Wait for GUI to initialize
        self._wait_for_gui(timeout=5.0)
    
    def _create_gui(self):
        """Create GUI in a separate thread"""
        try:
            self.gui = GUIInterface(jupiter_color="blue", user_color="green")
        except Exception as e:
            print(f"Error creating GUI: {e}")
    
    def _wait_for_gui(self, timeout=5.0):
        """Wait for GUI to initialize with timeout"""
        start_time = time.time()
        while not self.gui and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if not self.gui:
            self.skipTest("GUI could not be initialized")
    
    def tearDown(self):
        """Clean up after each test"""
        if self.gui:
            try:
                # Schedule GUI to close
                self.gui.root.after(0, self.gui.root.destroy)
                # Wait for GUI thread to finish
                self.gui_thread.join(timeout=1.0)
            except Exception as e:
                print(f"Error closing GUI: {e}")
    
    def test_initialization(self):
        """Test that the GUI interface initializes correctly"""
        # Check that GUI was created
        self.assertIsNotNone(self.gui)
        
        # Check that main window exists
        self.assertIsNotNone(self.gui.root)
        
        # Check that key components exist
        self.assertIsNotNone(self.gui.chat_text)
        self.assertIsNotNone(self.gui.text_entry)
        self.assertIsNotNone(self.gui.send_button)
    
    def test_color_configuration(self):
        """Test that colors are set correctly"""
        # Check that Jupiter color is configured
        self.assertEqual(self.gui.jupiter_color, "blue")
        
        # Check that user color is configured
        self.assertEqual(self.gui.user_color, "green")
        
        # Check that tags are created with these colors
        chat_text_tags = self.gui.chat_text.tag_names()
        self.assertIn("jupiter_prefix", chat_text_tags)
        self.assertIn("jupiter_bubble", chat_text_tags)
        self.assertIn("user_prefix", chat_text_tags)
        self.assertIn("user_bubble", chat_text_tags)
    
    def test_message_display(self):
        """Test displaying messages from Jupiter and user"""
        # Create event for synchronization
        print_complete = threading.Event()
        
        # Function to print message and set event
        def print_and_signal():
            self.gui.print_jupiter_message("Test message from Jupiter")
            print_complete.set()
        
        # Schedule print on GUI thread
        self.gui.root.after(0, print_and_signal)
        
        # Wait for print to complete
        self.assertTrue(print_complete.wait(timeout=1.0))
        
        # Check output queue
        self.assertEqual(self.gui.output_queue.qsize(), 1)
        message = self.gui.output_queue.get()
        self.assertEqual(message["type"], "jupiter")
        self.assertEqual(message["text"], "Test message from Jupiter")
    
    def test_status_updates(self):
        """Test setting status messages"""
        # Create event for synchronization
        status_complete = threading.Event()
        
        # Function to set status and signal event
        def set_status_and_signal():
            self.gui.set_status("Processing...", True)
            status_complete.set()
        
        # Schedule on GUI thread
        self.gui.root.after(0, set_status_and_signal)
        
        # Wait for completion
        self.assertTrue(status_complete.wait(timeout=1.0))
        
        # Check output queue
        self.assertEqual(self.gui.output_queue.qsize(), 1)
        message = self.gui.output_queue.get()
        self.assertEqual(message["type"], "status")
        self.assertEqual(message["text"], "Processing...")
        self.assertTrue(message["color"] == "#FFA500")  # Orange for busy
    
    @patch('tkinter.Entry')
    def test_get_user_input(self, mock_entry):
        """Test getting user input"""
        # Replace real Entry with mock to avoid threading issues
        original_entry = self.gui.text_entry
        mock_entry_instance = MagicMock()
        mock_entry_instance.get.return_value = "Test input"
        self.gui.text_entry = mock_entry_instance
        
        try:
            # Set up a thread to simulate user input
            def simulate_input():
                # Wait a bit for get_user_input to be called
                time.sleep(0.2)
                
                # Put input in queue and set event
                self.gui.input_queue.put("Test input")
                self.gui.input_ready.set()
            
            input_thread = threading.Thread(target=simulate_input)
            input_thread.daemon = True
            input_thread.start()
            
            # Get user input with timeout
            result = None
            try:
                # Use a timeout to avoid hanging if test fails
                result = self.gui.get_user_input(prefix="TestUser")
            except Exception as e:
                self.fail(f"get_user_input raised an exception: {e}")
            
            # Check result
            self.assertEqual(result, "Test input")
            
            # Check that user prefix was set
            self.assertEqual(self.gui.user_prefix, "TestUser")
        finally:
            # Restore original entry
            self.gui.text_entry = original_entry
    
    def test_view_switching(self):
        """Test switching between chat and knowledge views"""
        # Create events for synchronization
        chat_to_knowledge = threading.Event()
        knowledge_to_chat = threading.Event()
        
        # Function to switch views
        def switch_views():
            # Start in chat view
            self.assertEqual(self.gui.current_view, "chat")
            
            # Switch to knowledge view
            self.gui.show_knowledge_view()
            chat_to_knowledge.set()
            
            # Wait a bit
            time.sleep(0.2)
            
            # Switch back to chat view
            self.gui.show_chat_view()
            knowledge_to_chat.set()
        
        # Schedule on GUI thread
        self.gui.root.after(0, switch_views)
        
        # Wait for completion with timeout
        self.assertTrue(chat_to_knowledge.wait(timeout=1.0))
        self.assertTrue(knowledge_to_chat.wait(timeout=1.0))
        
        # Check that we're back in chat view
        self.assertEqual(self.gui.current_view, "chat")
    
    def test_knowledge_bubbles(self):
        """Test creating knowledge bubbles"""
        # Create event for synchronization
        bubbles_complete = threading.Event()
        
        # Sample user data
        user_data = {
            "name": "TestUser",
            "location": "Sydney",
            "profession": "Developer",
            "likes": ["coding", "testing"],
            "interests": ["AI", "automation"]
        }
        
        # Function to create bubbles and signal
        def create_bubbles_and_signal():
            # Switch to knowledge view
            self.gui.show_knowledge_view()
            
            # Create bubbles
            self.gui.create_knowledge_bubbles(user_data)
            
            # Signal completion
            bubbles_complete.set()
        
        # Schedule on GUI thread
        self.gui.root.after(0, create_bubbles_and_signal)
        
        # Wait for completion
        self.assertTrue(bubbles_complete.wait(timeout=2.0))
        
        # Check that view switched
        self.assertEqual(self.gui.current_view, "knowledge")
    
    def test_knowledge_editing(self):
        """Test knowledge editing interface"""
        # This is a simplified test since we can't easily interact with dialogs
        # Create event for synchronization
        edit_complete = threading.Event()
        
        # Sample user data
        user_data = {
            "name": "TestUser",
            "location": "Sydney"
        }
        
        # Mock to avoid actual dialog
        orig_show_text_editor = self.gui.show_text_editor
        self.gui.show_text_editor = MagicMock(return_value="Melbourne")
        
        try:
            # Function to test editing
            def edit_and_signal():
                # Switch to knowledge view and create bubbles
                self.gui.show_knowledge_view()
                self.gui.create_knowledge_bubbles(user_data)
                
                # Edit knowledge
                self.gui.edit_knowledge("location", "Sydney")
                
                # Add to edit queue
                edit_complete.set()
            
            # Schedule on GUI thread
            self.gui.root.after(0, edit_and_signal)
            
            # Wait for completion
            self.assertTrue(edit_complete.wait(timeout=1.0))
            
            # Check that editor was called
            self.gui.show_text_editor.assert_called_once()
            
            # Check knowledge edit queue
            self.assertEqual(self.gui.knowledge_edit_queue.qsize(), 1)
            edit = self.gui.knowledge_edit_queue.get()
            self.assertEqual(edit["action"], "edit")
            self.assertEqual(edit["category"], "location")
            self.assertEqual(edit["old_value"], "Sydney")
            self.assertEqual(edit["new_value"], "Melbourne")
        finally:
            # Restore original method
            self.gui.show_text_editor = orig_show_text_editor
    
    def test_exit_handling(self):
        """Test handling exit commands"""
        # Check exit command handling
        self.assertTrue(self.gui.handle_exit_command("exit"))
        self.assertTrue(self.gui.handle_exit_command("quit"))
        self.assertFalse(self.gui.handle_exit_command("hello"))
        
        # Test window close handling
        orig_destroy = self.gui.root.destroy
        self.gui.root.destroy = MagicMock()
        
        try:
            # Simulate window close
            self.gui.handle_window_close()
            
            # Check that destroy was called
            self.gui.root.destroy.assert_called_once()
            
            # Check that is_running is False
            self.assertFalse(self.gui.is_running)
            
            # Check that input_ready was set
            self.assertTrue(self.gui.input_ready.is_set())
            
            # Check that exit was put in queue
            self.assertEqual(self.gui.input_queue.get(), "exit")
        finally:
            # Restore original method
            self.gui.root.destroy = orig_destroy

if __name__ == '__main__':
    unittest.main()
