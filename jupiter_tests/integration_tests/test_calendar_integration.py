import os
import sys
import unittest
import tempfile
import datetime
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter modules
from core.chat_engine import ChatEngine
from models.user_model import UserModel
from models.llm_client import LLMClient
from utils.calendar.calendar_manager import CalendarManager
from utils.calendar.calendar_storage import CalendarStorage
from utils.calendar.calendar_commands import CalendarCommands
from utils.calendar.prompt_enhancer import PromptEnhancer

# Import test utilities
from test_utils.test_environment import setup_test_environment, cleanup_test_environment
from test_utils.test_helpers import TestUserInterface, TestLogger, create_test_calendar_db
from mocks.mock_llm import MockLLMClient

class TestCalendarIntegration(unittest.TestCase):
    """Test integration between Calendar components and ChatEngine"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        cls.test_env = setup_test_environment()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up test components for each test"""
        # Create a calendar database with test data
        self.db_path = create_test_calendar_db()
        
        # Create calendar components
        self.storage = CalendarStorage(self.db_path)
        self.calendar_manager = CalendarManager(self.storage)
        self.calendar_commands = CalendarCommands(self.calendar_manager)
        
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.user_data_file = os.path.join(self.temp_dir, 'test_user_data.json')
        self.prompt_folder = os.path.join(self.temp_dir, "prompts")
        self.logs_folder = os.path.join(self.temp_dir, "logs")
        
        # Create folders
        os.makedirs(self.prompt_folder, exist_ok=True)
        os.makedirs(self.logs_folder, exist_ok=True)
        
        # Create user model
        self.user_model = UserModel(self.user_data_file)
        self.user_model.set_current_user({"name": "TestUser"})
        self.user_model.save_current_user()
        
        # Create system prompt file
        with open(os.path.join(self.prompt_folder, "system_prompt.txt"), 'w', encoding='utf-8') as f:
            f.write("I am Jupiter, an AI assistant. I'm helpful and friendly.")
        
        # Create other components
        self.llm_client = MockLLMClient()
        self.logger = TestLogger()
        self.ui = TestUserInterface()
        
        # Set up config
        self.config = {
            "llm": {
                "provider": "ollama",
                "api_url": "http://localhost:11434",
                "default_model": "gemma3",
                "chat_temperature": 0.7,
                "extraction_temperature": 0.2,
                "token_limit": 8192
            },
            "paths": {
                "prompt_folder": self.prompt_folder,
                "logs_folder": self.logs_folder,
                "user_data_file": self.user_data_file
            },
            "ui": {
                "jupiter_color": "yellow",
                "user_color": "magenta"
            },
            "calendar": {
                "enable_notifications": True,
                "notification_check_interval": 1,
                "prompt_detail_level": "normal",
                "default_reminder_minutes": 15
            }
        }
        
        # Create the ChatEngine with test mode
        self.chat_engine = ChatEngine(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logger=self.logger,
            ui=self.ui,
            config=self.config,
            test_mode=True
        )
        
        # Path for calendar command processing
        self.original_process_calendar_command = None
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # Remove database file
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        
        # Restore patched function if needed
        if self.original_process_calendar_command:
            import utils.calendar
            utils.calendar.process_calendar_command = self.original_process_calendar_command
    
    def test_calendar_info_in_prompt(self):
        """Test that calendar info is included in the prompt"""
        # Create a prompt enhancer with our test calendar
        enhancer = PromptEnhancer(self.calendar_manager)
        
        # Patch the enhance_prompt function to use our test calendar
        with patch('utils.calendar.prompt_enhancer.enhance_prompt', side_effect=enhancer.enhance_prompt):
            # Prepare a message for the LLM
            prompt = self.chat_engine.prepare_message_for_llm("Hello Jupiter")
            
            # Check that calendar information is included in the prompt
            self.assertIn("Calendar Information", prompt)
            self.assertIn("Team Meeting", prompt)
            self.assertIn("Company Workshop", prompt)
    
    def test_calendar_command_handling(self):
        """Test that calendar commands are properly handled"""
        # Create a mock implementation to verify command processing
        calls = []
        
        def mock_process_calendar_command(user_id, command_text):
            calls.append((user_id, command_text))
            return f"Processed calendar command: {command_text}"
        
        # Patch the process_calendar_command function
        import utils.calendar
        self.original_process_calendar_command = utils.calendar.process_calendar_command
        utils.calendar.process_calendar_command = mock_process_calendar_command
        
        # Send a calendar command
        response = self.chat_engine.handle_user_commands("/calendar show events")
        
        # Check that the command was processed
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "TestUser")
        self.assertEqual(calls[0][1], "show events")
        self.assertIn("Processed calendar command", response)
    
    def test_calendar_commands_integration(self):
        """Test actual integration with calendar commands"""
        # Set up to use actual calendar commands
        import utils.calendar
        calendar_manager_backup = utils.calendar.default_manager
        
        try:
            # Replace default calendar manager with our test one
            utils.calendar.default_manager = self.calendar_manager
            
            # Test showing events
            response = self.chat_engine.handle_user_commands("/calendar show events")
            
            # Check that calendar events are in the response
            self.assertIn("Team Meeting", response)
            self.assertIn("Company Workshop", response)
            
            # Test adding an event
            tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            add_response = self.chat_engine.handle_user_commands(f"/calendar add New Test Event on {tomorrow} at 3:00 PM")
            
            # Check that event was added
            self.assertIn("Added event", add_response)
            self.assertIn("New Test Event", add_response)
            
            # Verify event was actually added
            show_response = self.chat_engine.handle_user_commands("/calendar show events")
            self.assertIn("New Test Event", show_response)
            
        finally:
            # Restore original default manager
            utils.calendar.default_manager = calendar_manager_backup
    
    def test_calendar_preferences_command(self):
        """Test handling of calendar preferences command"""
        # Mock the preferences UI function
        preferences_mock = MagicMock()
        
        with patch('utils.calendar.preferences_ui.show_preferences_dialog', preferences_mock):
            # Mock the UI root
            self.ui.root = MagicMock()
            
            # Send preferences command
            response = self.chat_engine.handle_user_commands("/calendar preferences")
            
            # Check that preferences UI would be shown
            self.assertTrue(self.ui.root.after.called)
            self.assertIn("preferences", response.lower())
    
    def test_prompt_enhancer_integration(self):
        """Test integration with prompt enhancer for different detail levels"""
        # Create a prompt enhancer with our test calendar
        enhancer = PromptEnhancer(self.calendar_manager)
        
        # Test different detail levels
        for detail_level in ['minimal', 'normal', 'detailed']:
            with patch('utils.calendar.prompt_enhancer.enhance_prompt', 
                      side_effect=lambda user_id, prompt, detail_level=detail_level: 
                      enhancer.enhance_prompt(user_id, prompt, detail_level)):
                
                # Update config with detail level
                self.config['calendar']['prompt_detail_level'] = detail_level
                
                # Prepare a message for the LLM
                prompt = self.chat_engine.prepare_message_for_llm("Hello Jupiter")
                
                # Minimal should only include today's events
                if detail_level == 'minimal':
                    self.assertIn("Team Meeting", prompt)  # Today's event
                    self.assertNotIn("Project Review", prompt)  # Future event
                
                # Normal should include events for next week
                elif detail_level == 'normal':
                    self.assertIn("Team Meeting", prompt)  # Today's event
                    self.assertIn("Company Workshop", prompt)  # Tomorrow's event
                
                # Detailed should include all events including future ones
                elif detail_level == 'detailed':
                    self.assertIn("Team Meeting", prompt)  # Today's event
                    self.assertIn("Company Workshop", prompt)  # Tomorrow's event
                    self.assertIn("Project Review", prompt)  # Next week's event

if __name__ == '__main__':
    unittest.main()
