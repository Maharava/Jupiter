import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter modules
from models.llm_client import LLMClient

# Import test utilities
from test_utils.test_environment import setup_test_environment, cleanup_test_environment
from test_utils.test_helpers import MockResponse, get_mock_llm_response

class TestLLMClient(unittest.TestCase):
    """Test cases for LLMClient class"""
    
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
        self.api_url = "http://test.ollama.local:11434"
        self.default_model = "test_model"
    
    def test_init(self):
        """Test LLMClient initialization"""
        # Normal initialization
        client = LLMClient(api_url=self.api_url, default_model=self.default_model)
        self.assertEqual(client.api_url, self.api_url)
        self.assertEqual(client.default_model, self.default_model)
        self.assertFalse(client.test_mode)
        
        # Test mode initialization
        test_client = LLMClient(api_url=self.api_url, default_model=self.default_model, test_mode=True)
        self.assertTrue(test_client.test_mode)
    
    @patch('models.llm_client.requests.post')
    def test_generate_chat_response(self, mock_post):
        """Test generating a chat response from the LLM"""
        # Mock successful API response
        mock_post.return_value = MockResponse({"response": "This is a test response from the LLM."})
        
        client = LLMClient(api_url=self.api_url, default_model=self.default_model)
        response = client.generate_chat_response("Hello, how are you?")
        
        # Check that the response was returned correctly
        self.assertEqual(response, "This is a test response from the LLM.")
        
        # Check that the API was called with correct parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['model'], self.default_model)
        self.assertEqual(kwargs['json']['prompt'], "Hello, how are you?")
        self.assertEqual(kwargs['json']['stream'], False)
        self.assertIn('temperature', kwargs['json']['options'])
    
    @patch('models.llm_client.requests.post')
    def test_generate_chat_response_api_error(self, mock_post):
        """Test handling API errors when generating a chat response"""
        # Mock API error
        mock_post.return_value = MockResponse({"error": "API error"}, status_code=500)
        
        client = LLMClient(api_url=self.api_url, default_model=self.default_model)
        response = client.generate_chat_response("Hello")
        
        # Check that an error message was returned
        self.assertTrue("Error" in response)
        self.assertTrue("500" in response)
    
    @patch('models.llm_client.requests.post')
    def test_generate_chat_response_connection_error(self, mock_post):
        """Test handling connection errors when generating a chat response"""
        # Mock connection error
        mock_post.side_effect = Exception("Connection error")
        
        client = LLMClient(api_url=self.api_url, default_model=self.default_model)
        response = client.generate_chat_response("Hello")
        
        # Check that an error message was returned
        self.assertTrue("Error" in response)
        self.assertTrue("Connection error" in response)
    
    def test_generate_chat_response_test_mode(self):
        """Test generating a chat response in test mode"""
        client = LLMClient(api_url=self.api_url, default_model=self.default_model, test_mode=True)
        
        # Test mode should return a placeholder response without making API calls
        response = client.generate_chat_response("Hello")
        
        # Check that a test mode message was returned
        self.assertTrue("TEST MODE" in response)
    
    @patch('models.llm_client.requests.post')
    def test_extract_information(self, mock_post):
        """Test extracting information from conversation text"""
        # Mock successful API response
        extracted_info = {
            "extracted_info": [
                {"category": "name", "value": "John Smith"},
                {"category": "location", "value": "Melbourne"}
            ]
        }
        mock_post.return_value = MockResponse({"response": json.dumps(extracted_info)})
        
        client = LLMClient(api_url=self.api_url, default_model=self.default_model)
        
        # Sample conversation
        conversation = """
        User: Hi, I'm John Smith from Melbourne.
        Jupiter: Nice to meet you, John!
        """
        
        # Extract information
        response = client.extract_information("Extract user information", conversation)
        
        # Check that the extraction was successful
        self.assertIn("John Smith", response)
        self.assertIn("Melbourne", response)
        
        # Parse the response to verify structure
        import json
        extracted = json.loads(response)
        self.assertIn("extracted_info", extracted)
        self.assertEqual(len(extracted["extracted_info"]), 2)
        
        # Check API call parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['model'], self.default_model)
        self.assertIn("Extract user information", kwargs['json']['prompt'])
        self.assertIn(conversation, kwargs['json']['prompt'])
        self.assertEqual(kwargs['json']['options']['temperature'], 0.2)  # Lower temperature for extraction
    
    def test_extract_information_test_mode(self):
        """Test extracting information in test mode"""
        client = LLMClient(api_url=self.api_url, default_model=self.default_model, test_mode=True)
        
        # Test mode should return a minimal JSON response
        response = client.extract_information("Extract user information", "Test conversation")
        
        # Check response format
        import json
        extracted = json.loads(response)
        self.assertIn("extracted_info", extracted)
        self.assertEqual(len(extracted["extracted_info"]), 0)  # Empty in test mode
    
    # This test needs to import json module
    import json

if __name__ == '__main__':
    unittest.main()
