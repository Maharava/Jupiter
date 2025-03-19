import os
import sys
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter modules
from core.chat_engine import ChatEngine
from models.user_model import UserModel
from models.llm_client import LLMClient
from utils.logger import Logger

# Import test utilities
from test_utils.test_environment import setup_test_environment, cleanup_test_environment
from test_utils.test_helpers import TestUserInterface, TestLogger
from mocks.mock_llm import MockLLMClient

class TestFirstTimeUserExperience(unittest.TestCase):
    """
    Test the complete experience for a first-time user.
    
    This covers:
    - Initial greeting and name collection
    - First conversation with information extraction
    - Memory storage and retrieval
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
        """Set up test components for each test"""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.user_data_file = os.path.join(self.temp_dir, 'test_user_data.json')
        self.prompt_folder = os.path.join(self.temp_dir, "prompts")
        self.logs_folder = os.path.join(self.temp_dir, "logs")
        
        # Create folders
        os.makedirs(self.prompt_folder, exist_ok=True)
        os.makedirs(self.logs_folder, exist_ok=True)
        
        # Create empty user data file (no existing users)
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump({"known_users": {}}, f)
        
        # Create system prompt file
        with open(os.path.join(self.prompt_folder, "system_prompt.txt"), 'w', encoding='utf-8') as f:
            f.write("I am Jupiter, an AI assistant. I'm helpful and friendly.")
        
        # Create other components
        self.user_model = UserModel(self.user_data_file)
        self.llm_client = MockLLMClient()
        self.logger = TestLogger(logs_folder=self.logs_folder)
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
            }
        }
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_first_time_flow(self):
        """Test the complete first-time user flow"""
        # Create ChatEngine with our components
        chat_engine = ChatEngine(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logger=self.logger,
            ui=self.ui,
            config=self.config,
            test_mode=True
        )
        
        # Mock the UI flow for first-time user
        self.ui.set_inputs([
            # First input will be the name for initial greeting
            "FirstTimeUser",
            # Regular conversation
            "Hello Jupiter! I'm a software engineer from Melbourne.",
            "I enjoy programming and hiking on weekends.",
            # Check memory
            "/memory",
            # Exit command
            "exit"
        ])
        
        # Run the chat
        chat_engine.run()
        
        # Analyze the conversation
        messages = self.ui.messages
        
        # Check initial greeting
        initial_messages = [msg for msg in messages[:3] if msg["role"] == "Jupiter"]
        greeting_text = "\n".join([msg["message"] for msg in initial_messages])
        self.assertIn("Jupiter", greeting_text)
        self.assertIn("name", greeting_text.lower())
        
        # Check welcome message after entering name
        welcome_messages = [msg for msg in messages[3:6] if msg["role"] == "Jupiter"]
        welcome_text = "\n".join([msg["message"] for msg in welcome_messages])
        self.assertIn("FirstTimeUser", welcome_text)
        
        # Check memory response
        memory_message = None
        for msg in messages:
            if msg["role"] == "Jupiter" and "I remember" in msg["message"]:
                memory_message = msg["message"]
                break
        
        self.assertIsNotNone(memory_message)
        self.assertIn("Melbourne", memory_message)
        self.assertIn("software engineer", memory_message.lower())
        
        # Verify user data was saved
        saved_data = json.load(open(self.user_data_file, 'r', encoding='utf-8'))
        self.assertIn("known_users", saved_data)
        self.assertIn("FirstTimeUser", saved_data["known_users"])
        
        user_data = saved_data["known_users"]["FirstTimeUser"]
        self.assertEqual(user_data["name"], "FirstTimeUser")
        
        # Check logger recorded the conversation
        log_entries = self.logger.logs
        self.assertGreaterEqual(len(log_entries), 5)  # At least 5 log entries
        
        # Verify log file was created
        log_file = self.logger.current_log_file
        self.assertIsNotNone(log_file)
        self.assertTrue(os.path.exists(log_file))
    
    def test_information_extraction(self):
        """Test that information is extracted from conversation and stored"""
        # Configure the mock LLM to return specific extracted information
        original_extract = self.llm_client.extract_information
        
        def mock_extract_information(prompt, conversation, temperature=0.2):
            # Return different extraction results based on conversation content
            if "Melbourne" in conversation:
                return json.dumps({
                    "extracted_info": [
                        {"category": "location", "value": "Melbourne"}
                    ]
                })
            elif "software engineer" in conversation:
                return json.dumps({
                    "extracted_info": [
                        {"category": "profession", "value": "software engineer"}
                    ]
                })
            elif "hiking" in conversation:
                return json.dumps({
                    "extracted_info": [
                        {"category": "hobbies", "value": "hiking"}
                    ]
                })
            return json.dumps({"extracted_info": []})
        
        self.llm_client.extract_information = mock_extract_information
        
        # Create the InfoExtractor
        from core.info_extractor import InfoExtractor
        info_extractor = InfoExtractor(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logs_folder=self.logs_folder,
            prompt_folder=self.prompt_folder,
            ui=self.ui,
            test_mode=False
        )
        
        # Create test log with information to extract
        log_file = os.path.join(self.logs_folder, 'test_extraction.log')
        log_content = """=== Jupiter Chat Session ===

[2023-01-01 12:01:00] ExtractionTest: Hello Jupiter!

[2023-01-01 12:01:10] Jupiter: Hello ExtractionTest! How can I help you today?

[2023-01-01 12:01:20] ExtractionTest: I'm a software engineer from Melbourne.

[2023-01-01 12:01:30] Jupiter: That's great! What kind of software do you work on?

[2023-01-01 12:01:40] ExtractionTest: I develop web applications. I also enjoy hiking on weekends.

[2023-01-01 12:01:50] Jupiter: That sounds wonderful! Melbourne has some great hiking trails nearby.
"""
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        # Process the log file
        info_extractor.process_log_file(log_file)
        
        # Check that user data was updated
        user_data = self.user_model.get_user("ExtractionTest")
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data["name"], "ExtractionTest")
        self.assertEqual(user_data["location"], "Melbourne")
        self.assertEqual(user_data["profession"], "software engineer")
        self.assertIn("hiking", user_data["hobbies"])
        
        # Restore original extract method
        self.llm_client.extract_information = original_extract
    
    def test_name_command_for_new_user(self):
        """Test that the /name command works correctly for first-time users"""
        # Create ChatEngine with our components
        chat_engine = ChatEngine(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logger=self.logger,
            ui=self.ui,
            config=self.config,
            test_mode=True
        )
        
        # Set current user to a temporary name
        chat_engine.user_model.set_current_user({"name": "TempUser"})
        
        # Handle name command
        response = chat_engine.handle_user_commands("/name CommandTest")
        
        # Check that response is appropriate
        self.assertIn("CommandTest", response)
        
        # Check that user data was updated
        self.assertEqual(chat_engine.user_model.current_user["name"], "CommandTest")
        
        # Check that user was saved
        user_data = json.load(open(self.user_data_file, 'r', encoding='utf-8'))
        self.assertIn("known_users", user_data)
        self.assertIn("CommandTest", user_data["known_users"])
        
        # Check that original name is no longer there
        self.assertNotIn("TempUser", user_data["known_users"])

if __name__ == '__main__':
    unittest.main()
