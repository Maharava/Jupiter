import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter modules
from models.user_model import UserModel
from models.llm_client import LLMClient
from core.chat_engine import ChatEngine
from utils.logger import Logger

# Import mocks
from mocks.mock_llm import MockLLMClient

# Import test utilities
from test_utils.test_environment import setup_test_environment, cleanup_test_environment
from test_utils.test_helpers import TestUserInterface, TestLogger

class TestChatUserIntegration(unittest.TestCase):
    """Test integration between ChatEngine and UserModel"""
    
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
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        
        # Create user data file
        self.user_data_file = os.path.join(self.temp_dir, 'test_user_data.json')
        
        # Create components
        self.user_model = UserModel(self.user_data_file)
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
                "prompt_folder": os.path.join(self.temp_dir, "prompts"),
                "logs_folder": os.path.join(self.temp_dir, "logs"),
                "user_data_file": self.user_data_file
            },
            "ui": {
                "jupiter_color": "yellow",
                "user_color": "magenta"
            }
        }
        
        # Create prompts folder
        os.makedirs(os.path.join(self.temp_dir, "prompts"), exist_ok=True)
        
        # Create system prompt
        with open(os.path.join(self.temp_dir, "prompts", "system_prompt.txt"), 'w', encoding='utf-8') as f:
            f.write("I am Jupiter, an AI assistant. I'm helpful and friendly.")
        
        # Create the ChatEngine
        self.chat_engine = ChatEngine(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logger=self.logger,
            ui=self.ui,
            config=self.config,
            test_mode=True
        )
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_user_information_in_prompt(self):
        """Test that user information is included in the prompt"""
        # Set up user data
        self.user_model.set_current_user({
            "name": "IntegrationTest",
            "location": "Brisbane",
            "profession": "Software Engineer",
            "likes": ["Python", "testing"]
        })
        
        # Prepare a message for the LLM
        prompt = self.chat_engine.prepare_message_for_llm("Hello Jupiter")
        
        # Check that user information is included in the prompt
        self.assertIn("IntegrationTest", prompt)
        self.assertIn("Brisbane", prompt)
        self.assertIn("Software Engineer", prompt)
        self.assertIn("Python", prompt)
        self.assertIn("testing", prompt)
    
    def test_format_user_information(self):
        """Test formatting user information for the prompt"""
        # Set up user data with various types of fields
        self.user_model.set_current_user({
            "name": "FormatTest",
            "location": "Melbourne",
            "profession": "Data Scientist",
            "likes": ["coffee", "data"],
            "dislikes": ["meetings"],
            "age": 30
        })
        
        # Get formatted information
        formatted_info = self.chat_engine.format_user_information()
        
        # Check that information is formatted correctly
        self.assertIn("What You Know About The User", formatted_info)
        self.assertIn("- Name: FormatTest", formatted_info)
        self.assertIn("- Location: Melbourne", formatted_info)
        self.assertIn("- Profession: Data Scientist", formatted_info)
        self.assertIn("- Likes: coffee, data", formatted_info)
        self.assertIn("- Dislikes: meetings", formatted_info)
        self.assertIn("- Age: 30", formatted_info)
    
    def test_name_command_updates_user(self):
        """Test that the /name command updates the user model"""
        # Set an initial user
        self.user_model.set_current_user({"name": "InitialName"})
        
        # Use the name command
        response = self.chat_engine.handle_user_commands("/name NewName")
        
        # Check that the command was processed
        self.assertIsNotNone(response)
        self.assertIn("NewName", response)
        
        # Check that the user model was updated
        self.assertEqual(self.user_model.current_user["name"], "NewName")
        
        # Load the user data file to verify it was saved
        user_data = self.user_model.load_all_users()
        self.assertIn("known_users", user_data)
        self.assertIn("NewName", user_data["known_users"])
    
    def test_memory_display(self):
        """Test formatting memory display for the user"""
        # Set up user data with various types of fields
        self.user_model.set_current_user({
            "name": "MemoryTest",
            "location": "Sydney",
            "profession": "Teacher",
            "likes": ["reading", "travel"],
            "family": {"spouse": "Partner", "children": 2},
            "interests": ["history", "science"],
            "important_dates": ["2023-01-15: Anniversary"]
        })
        
        # Handle memory command
        response = self.chat_engine.handle_user_commands("/memory")
        
        # Check that memory information is formatted correctly
        self.assertIn("what I remember about you", response.lower())
        self.assertIn("Sydney", response)
        self.assertIn("Teacher", response)
        self.assertIn("reading", response)
        self.assertIn("travel", response)
        self.assertIn("history", response)
        self.assertIn("science", response)
    
    def test_conversation_flow(self):
        """Test the conversation flow between UI, chat engine, and user model"""
        # Set up a sequence of interactions
        self.ui.set_inputs([
            "My name is FlowTest",
            "I'm a developer from Perth",
            "I enjoy surfing and coding",
            "/memory",
            "exit"
        ])
        
        # Mock the handle_initial_greeting to skip the name prompt
        original_greeting = self.chat_engine.handle_initial_greeting
        self.chat_engine.handle_initial_greeting = lambda: None
        
        # Set the current user
        self.user_model.set_current_user({"name": "FlowTest"})
        
        # Mock the logger to not create actual files
        self.chat_engine.logger = self.logger
        
        # Run the chat engine
        self.chat_engine.run()
        
        # Restore original method
        self.chat_engine.handle_initial_greeting = original_greeting
        
        # Analyze the conversation messages
        messages = self.ui.messages
        jupiter_responses = [msg["message"] for msg in messages if msg["role"] == "Jupiter"]
        
        # Check that Jupiter responded to each message
        self.assertGreaterEqual(len(jupiter_responses), 3)
        
        # Check memory response
        memory_response = None
        for msg in messages:
            if msg["role"] == "Jupiter" and "I remember" in msg["message"]:
                memory_response = msg["message"]
                break
                
        self.assertIsNotNone(memory_response)
        self.assertIn("Perth", memory_response)
        
        # Check that logs were created
        self.assertGreaterEqual(len(self.logger.logs), 4)

if __name__ == '__main__':
    unittest.main()
