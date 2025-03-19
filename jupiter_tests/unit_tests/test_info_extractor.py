import os
import sys
import unittest
import json
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter modules
from core.info_extractor import InfoExtractor
from models.user_model import UserModel
from models.llm_client import LLMClient

# Import test utilities
from test_utils.test_environment import setup_test_environment, cleanup_test_environment
from test_utils.test_helpers import MockResponse

class TestInfoExtractor(unittest.TestCase):
    """Test cases for InfoExtractor class"""
    
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
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.logs_folder = os.path.join(self.temp_dir, 'logs')
        self.prompt_folder = os.path.join(self.temp_dir, 'prompts')
        os.makedirs(self.logs_folder, exist_ok=True)
        os.makedirs(self.prompt_folder, exist_ok=True)
        
        # Create a temporary user data file
        self.user_data_file = os.path.join(self.temp_dir, 'test_user_data.json')
        
        # Create a user model with the temp file
        self.user_model = UserModel(self.user_data_file)
        
        # Create a processed logs file
        self.processed_logs_file = os.path.join(self.logs_folder, 'processed_logs.json')
        with open(self.processed_logs_file, 'w', encoding='utf-8') as f:
            json.dump({"processed": []}, f)
        
        # Create an extraction prompt file
        self.extraction_prompt_file = os.path.join(self.prompt_folder, 'extraction_prompt.txt')
        with open(self.extraction_prompt_file, 'w', encoding='utf-8') as f:
            f.write("""
            You are an information extraction agent for Jupiter.
            
            Extract information in this format:
            {
              "extracted_info": [
                {"category": "name", "value": "John Smith"},
                {"category": "likes", "value": "vintage cars"}
              ]
            }
            """)
        
        # Create a mock LLM client
        self.llm_client = MagicMock(spec=LLMClient)
        self.llm_client.extract_information.return_value = json.dumps({
            "extracted_info": [
                {"category": "name", "value": "TestUser"},
                {"category": "location", "value": "Sydney"}
            ]
        })
        
        # Create the InfoExtractor
        self.info_extractor = InfoExtractor(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logs_folder=self.logs_folder,
            prompt_folder=self.prompt_folder,
            ui=None,
            test_mode=False
        )
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_load_extraction_prompt(self):
        """Test loading the extraction prompt from file"""
        # Call the method to load the prompt
        prompt = self.info_extractor.load_extraction_prompt()
        
        # Check that the prompt was loaded correctly
        self.assertIn("extraction agent", prompt)
        self.assertIn("extracted_info", prompt)
    
    def test_load_extraction_prompt_default(self):
        """Test creating a default extraction prompt if none exists"""
        # Remove the existing prompt file
        os.remove(self.extraction_prompt_file)
        
        # Call the method to load the prompt
        prompt = self.info_extractor.load_extraction_prompt()
        
        # Check that a default prompt was created
        self.assertTrue(os.path.exists(self.extraction_prompt_file))
        self.assertIn("extraction agent", prompt)
        self.assertIn("extracted_info", prompt)
    
    def test_load_processed_logs(self):
        """Test loading the list of processed logs"""
        # Call the method to load processed logs
        processed_logs = self.info_extractor.load_processed_logs()
        
        # Check that the processed logs were loaded correctly
        self.assertIn("processed", processed_logs)
        self.assertEqual(len(processed_logs["processed"]), 0)
    
    def test_mark_log_as_processed(self):
        """Test marking a log file as processed"""
        # Create a test log file
        test_log = os.path.join(self.logs_folder, 'test_log.log')
        with open(test_log, 'w', encoding='utf-8') as f:
            f.write("Test log content")
        
        # Mark the log as processed
        self.info_extractor.mark_log_as_processed(test_log)
        
        # Check that the log was added to the processed list
        processed_logs = self.info_extractor.load_processed_logs()
        self.assertIn(test_log, processed_logs["processed"])
    
    def test_get_unprocessed_logs(self):
        """Test getting the list of unprocessed logs"""
        # Create some test log files
        processed_log = os.path.join(self.logs_folder, 'jupiter_chat_processed.log')
        unprocessed_log = os.path.join(self.logs_folder, 'jupiter_chat_unprocessed.log')
        not_log_file = os.path.join(self.logs_folder, 'not_a_log_file.txt')
        
        with open(processed_log, 'w', encoding='utf-8') as f:
            f.write("Processed log content")
        with open(unprocessed_log, 'w', encoding='utf-8') as f:
            f.write("Unprocessed log content")
        with open(not_log_file, 'w', encoding='utf-8') as f:
            f.write("Not a log file")
        
        # Mark the processed log as processed
        self.info_extractor.mark_log_as_processed(processed_log)
        
        # Get unprocessed logs
        unprocessed_logs = self.info_extractor.get_unprocessed_logs()
        
        # Check that only the unprocessed log is in the list
        self.assertIn(unprocessed_log, unprocessed_logs)
        self.assertNotIn(processed_log, unprocessed_logs)
        self.assertNotIn(not_log_file, unprocessed_logs)
    
    def test_read_log_file(self):
        """Test reading and parsing a log file"""
        # Create a test log file
        test_log = os.path.join(self.logs_folder, 'test_read.log')
        log_content = """=== Jupiter Chat Session: 2023-01-01 12:00:00 ===

    [2023-01-01 12:01:00] TestUser: Hello Jupiter!

    [2023-01-01 12:01:10] Jupiter: Hello TestUser! How can I help you today?

    [2023-01-01 12:01:20] TestUser: I'm looking for information about AI.

    [2023-01-01 12:01:30] Jupiter: I'd be happy to help with that!

    """
        with open(test_log, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        # Read the log file
        messages, user_prefix = self.info_extractor.read_log_file(test_log)
        
        # Check that the messages were parsed correctly
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["role"], "TestUser")  # No colon, matching current behavior
        self.assertEqual(messages[0]["message"], "Hello Jupiter!")
        self.assertEqual(messages[1]["role"], "Jupiter")
        self.assertEqual(messages[2]["role"], "TestUser")
        self.assertEqual(user_prefix, "TestUser:")
    
    def test_parse_llm_response(self):
        """Test parsing the LLM response"""
        # Test with valid JSON
        valid_response = """
        {
          "extracted_info": [
            {"category": "name", "value": "John"},
            {"category": "location", "value": "Melbourne"}
          ]
        }
        """
        extracted = self.info_extractor.parse_llm_response(valid_response)
        self.assertEqual(len(extracted), 2)
        self.assertEqual(extracted[0]["category"], "name")
        self.assertEqual(extracted[0]["value"], "John")
        
        # Test with valid JSON embedded in text
        embedded_response = """
        Here's the extracted information:
        {
          "extracted_info": [
            {"category": "profession", "value": "Engineer"}
          ]
        }
        """
        extracted = self.info_extractor.parse_llm_response(embedded_response)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["category"], "profession")
        
        # Test with invalid JSON
        invalid_response = "This is not JSON"
        extracted = self.info_extractor.parse_llm_response(invalid_response)
        self.assertEqual(len(extracted), 0)
        
        # Test with None
        extracted = self.info_extractor.parse_llm_response(None)
        self.assertEqual(len(extracted), 0)
    
    def test_identify_username_from_log(self):
        """Test identifying the username from a log file"""
        # Create a test log file
        test_log = os.path.join(self.logs_folder, 'test_username.log')
        log_content = """=== Jupiter Chat Session: 2023-01-01 12:00:00 ===

[2023-01-01 12:01:00] DifferentUser: Hello Jupiter!

[2023-01-01 12:01:10] Jupiter: Hello DifferentUser!

[2023-01-01 12:01:20] DifferentUser: How are you today?

[2023-01-01 12:01:30] Jupiter: I'm doing well, thank you!

"""
        with open(test_log, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        # Identify username
        username = self.info_extractor.identify_username_from_log(test_log)
        
        # Check that the username was identified correctly
        self.assertEqual(username, "DifferentUser")
    
    def test_process_log_file(self):
        """Test processing a log file"""
        # Create a test log file
        test_log = os.path.join(self.logs_folder, 'test_process.log')
        log_content = """=== Jupiter Chat Session: 2023-01-01 12:00:00 ===

[2023-01-01 12:01:00] ProcessUser: Hello Jupiter!

[2023-01-01 12:01:10] Jupiter: Hello ProcessUser!

[2023-01-01 12:01:20] ProcessUser: I'm a software developer from Brisbane.

[2023-01-01 12:01:30] Jupiter: That's great! I'd love to hear more about your work.

"""
        with open(test_log, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        # Mock the LLM response for this specific log
        self.llm_client.extract_information.return_value = json.dumps({
            "extracted_info": [
                {"category": "name", "value": "ProcessUser"},
                {"category": "profession", "value": "software developer"},
                {"category": "location", "value": "Brisbane"}
            ]
        })
        
        # Process the log file
        self.info_extractor.process_log_file(test_log)
        
        # Check that the log was marked as processed
        processed_logs = self.info_extractor.load_processed_logs()
        self.assertIn(test_log, processed_logs["processed"])
        
        # Check that the user data was updated
        user_data = self.user_model.get_user("ProcessUser")
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data["name"], "ProcessUser")
        self.assertEqual(user_data["profession"], "software developer")
        self.assertEqual(user_data["location"], "Brisbane")
    
    def test_process_log_file_test_mode(self):
        """Test processing a log file in test mode"""
        # Create a test log file
        test_log = os.path.join(self.logs_folder, 'test_mode.log')
        with open(test_log, 'w', encoding='utf-8') as f:
            f.write("Test log content")
        
        # Set test mode
        self.info_extractor.test_mode = True
        
        # Process the log file
        self.info_extractor.process_log_file(test_log)
        
        # In test mode, the log should be marked as processed without actually processing
        processed_logs = self.info_extractor.load_processed_logs()
        self.assertIn(test_log, processed_logs["processed"])
        
        # The LLM client should not have been called
        self.llm_client.extract_information.assert_not_called()
    
    def test_process_all_unprocessed_logs(self):
        """Test processing all unprocessed logs"""
        # Create some test log files
        log1 = os.path.join(self.logs_folder, 'jupiter_chat_log1.log')
        log2 = os.path.join(self.logs_folder, 'jupiter_chat_log2.log')
        
        with open(log1, 'w', encoding='utf-8') as f:
            f.write("""=== Jupiter Chat Session ===
[2023-01-01 12:01:00] User1: Hello Jupiter!
[2023-01-01 12:01:10] Jupiter: Hello User1!
""")
        
        with open(log2, 'w', encoding='utf-8') as f:
            f.write("""=== Jupiter Chat Session ===
[2023-01-01 12:02:00] User2: Hello Jupiter!
[2023-01-01 12:02:10] Jupiter: Hello User2!
""")
        
        # Process all unprocessed logs
        self.info_extractor.process_all_unprocessed_logs()
        
        # Check that all logs were marked as processed
        processed_logs = self.info_extractor.load_processed_logs()
        self.assertIn(log1, processed_logs["processed"])
        self.assertIn(log2, processed_logs["processed"])
        
        # The LLM client should have been called for each log
        self.assertEqual(self.llm_client.extract_information.call_count, 2)

if __name__ == '__main__':
    unittest.main()
