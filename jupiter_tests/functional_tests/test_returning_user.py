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

class TestReturningUserExperience(unittest.TestCase):
    """
    Test the complete experience for a returning user.
    
    This covers:
    - User recognition and loading of existing profile
    - Welcome back greeting with correct name
    - Using previously stored information in conversation
    - Adding new information to existing profile
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
        
        # Create user data file with existing users
        existing_users = {
            "known_users": {
                "ReturningUser": {
                    "name": "ReturningUser",
                    "location": "Sydney",
                    "profession": "Data Scientist",
                    "likes": ["coffee", "data visualization"],
                    "interests": ["AI", "machine learning"]
                },
                "CaseSensitiveTest": {
                    "name": "CaseSensitiveTest",
                    "location": "Brisbane"
                }
            }
        }
        
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump(existing_users, f, indent=4)
        
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
    
    def test_returning_user_recognition(self):
        """Test that returning users are recognized correctly"""
        # Create ChatEngine with our components
        chat_engine = ChatEngine(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logger=self.logger,
            ui=self.ui,
            config=self.config,
            test_mode=True
        )
        
        # Mock the UI flow for returning user
        self.ui.set_inputs([
            # First input will be the name for initial greeting
            "ReturningUser",
            # Regular conversation
            "Hello Jupiter! Do you remember me?",
            "What do you know about me?",
            # Check memory
            "/memory",
            # Exit command
            "exit"
        ])
        
        # Run the chat
        chat_engine.run()
        
        # Analyze the conversation
        messages = self.ui.messages
        
        # Check welcome back message
        welcome_messages = [msg for msg in messages if msg["role"] == "Jupiter" and "Welcome back" in msg["message"]]
        self.assertGreaterEqual(len(welcome_messages), 1)
        welcome_text = welcome_messages[0]["message"]
        self.assertIn("ReturningUser", welcome_text)
        
        # Check memory response
        memory_message = None
        for msg in messages:
            if msg["role"] == "Jupiter" and "/memory" in msg["message"]:
                memory_message = msg["message"]
                break
        
        self.assertIsNotNone(memory_message)
        self.assertIn("Sydney", memory_message)
        self.assertIn("Data Scientist", memory_message)
        self.assertIn("coffee", memory_message)
        self.assertIn("AI", memory_message)
    
    def test_case_insensitive_recognition(self):
        """Test that users are recognized regardless of case"""
        # Create ChatEngine with our components
        chat_engine = ChatEngine(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logger=self.logger,
            ui=self.ui,
            config=self.config,
            test_mode=True
        )
        
        # Mock the UI flow with different case for name
        self.ui.set_inputs([
            # First input with different case than stored
            "casesensitivetest",
            # Regular conversation
            "Hello! I'm back!",
            # Exit command
            "exit"
        ])
        
        # Run the chat
        chat_engine.run()
        
        # Analyze the conversation
        messages = self.ui.messages
        
        # Check welcome back message
        welcome_messages = [msg for msg in messages if msg["role"] == "Jupiter" and "Welcome back" in msg["message"]]
        self.assertGreaterEqual(len(welcome_messages), 1)
        welcome_text = welcome_messages[0]["message"]
        
        # Should use the original capitalization from storage
        self.assertIn("CaseSensitiveTest", welcome_text)
        
        # Check that current user is set correctly
        self.assertEqual(chat_engine.user_model.current_user["name"], "CaseSensitiveTest")
    
    def test_updating_existing_profile(self):
        """Test that new information is added to existing profiles"""
        # Configure the mock LLM to return specific extracted information
        original_extract = self.llm_client.extract_information
        
        def mock_extract_information(prompt, conversation, temperature=0.2):
            # Return extraction that adds new information about the user
            if "new hobby" in conversation.lower():
                return json.dumps({
                    "extracted_info": [
                        {"category": "hobbies", "value": "photography"}
                    ]
                })
            elif "favorite food" in conversation.lower():
                return json.dumps({
                    "extracted_info": [
                        {"category": "likes", "value": "pasta"}
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
        
        # Load returning user data
        self.user_model.set_current_user(self.user_model.get_user("ReturningUser"))
        
        # Create test log with information to extract
        log_file = os.path.join(self.logs_folder, 'test_update.log')
        log_content = """=== Jupiter Chat Session ===

[2023-01-01 12:01:00] ReturningUser: Hey Jupiter, I have a new hobby now - photography!

[2023-01-01 12:01:10] Jupiter: That's fantastic! Photography is a great hobby.

[2023-01-01 12:01:20] ReturningUser: Yes, and my favorite food is pasta.

[2023-01-01 12:01:30] Jupiter: Pasta is delicious! Do you have a favorite type?
"""
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        # Process the log file
        info_extractor.process_log_file(log_file)
        
        # Check that user data was updated with new information
        user_data = self.user_model.get_user("ReturningUser")
        self.assertIsNotNone(user_data)
        
        # Check that original data is still there
        self.assertEqual(user_data["name"], "ReturningUser")
        self.assertEqual(user_data["location"], "Sydney")
        self.assertEqual(user_data["profession"], "Data Scientist")
        self.assertIn("coffee", user_data["likes"])
        self.assertIn("data visualization", user_data["likes"])
        
        # Check that new data was added
        self.assertIn("photography", user_data["hobbies"])
        self.assertIn("pasta", user_data["likes"])
        
        # Check that file was updated
        saved_data = json.load(open(self.user_data_file, 'r', encoding='utf-8'))
        updated_user = saved_data["known_users"]["ReturningUser"]
        self.assertIn("photography", updated_user["hobbies"])
        self.assertIn("pasta", updated_user["likes"])
        
        # Restore original extract method
        self.llm_client.extract_information = original_extract
    
    def test_prompt_includes_user_information(self):
        """Test that the prompt includes user information for a returning user"""
        # Create ChatEngine with our components
        chat_engine = ChatEngine(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logger=self.logger,
            ui=self.ui,
            config=self.config,
            test_mode=True
        )
        
        # Load returning user data
        chat_engine.user_model.set_current_user(
            chat_engine.user_model.get_user("ReturningUser")
        )
        
        # Prepare a message for the LLM
        prompt = chat_engine.prepare_message_for_llm("Hello Jupiter")
        
        # Check that user information is included in the prompt
        self.assertIn("What You Know About The User", prompt)
        self.assertIn("ReturningUser", prompt)
        self.assertIn("Sydney", prompt)
        self.assertIn("Data Scientist", prompt)
        self.assertIn("coffee", prompt)
        self.assertIn("AI", prompt)
        self.assertIn("machine learning", prompt)
    
    def test_conversation_history_management(self):
        """Test that conversation history is managed correctly"""
        # Create ChatEngine with our components
        chat_engine = ChatEngine(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logger=self.logger,
            ui=self.ui,
            config=self.config,
            test_mode=True
        )
        
        # Load returning user data
        chat_engine.user_model.set_current_user(
            chat_engine.user_model.get_user("ReturningUser")
        )
        
        # Have a conversation
        chat_engine.conversation_history.clear()
        
        # Add messages to conversation history
        chat_engine.conversation_history.append("ReturningUser: Hello Jupiter!")
        chat_engine.conversation_history.append("Jupiter: Hello ReturningUser! How can I help you today?")
        chat_engine.conversation_history.append("ReturningUser: What's the weather like?")
        chat_engine.conversation_history.append("Jupiter: I don't have access to current weather information.")
        
        # Prepare a message for the LLM
        prompt = chat_engine.prepare_message_for_llm("Tell me about AI")
        
        # Check that conversation history is included in the prompt
        for message in chat_engine.conversation_history:
            self.assertIn(message, prompt)
        
        # Check that the new message is included
        self.assertIn("ReturningUser: Tell me about AI", prompt)

if __name__ == '__main__':
    unittest.main()
