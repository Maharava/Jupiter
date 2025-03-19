import os
import sys
import unittest
import json
import tempfile

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter modules
from models.user_model import UserModel

# Import test utilities
from test_utils.test_environment import TEST_ENV, setup_test_environment, cleanup_test_environment
from test_utils.test_helpers import compare_user_data

class TestUserModel(unittest.TestCase):
    """Test cases for UserModel class"""
    
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
        # Create a temporary user data file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        
        # Create a user model with the temp file
        self.user_model = UserModel(self.temp_file.name)
        
        # Create some test users
        test_users = {
            "known_users": {
                "TestUser": {
                    "name": "TestUser",
                    "location": "Sydney",
                    "likes": ["testing", "Python"]
                },
                "AnotherUser": {
                    "name": "AnotherUser",
                    "profession": "Developer",
                    "interests": ["AI", "automation"]
                }
            }
        }
        
        # Save test users to file
        with open(self.temp_file.name, 'w', encoding='utf-8') as f:
            json.dump(test_users, f)
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_load_all_users(self):
        """Test loading all users from file"""
        all_users = self.user_model.load_all_users()
        
        # Check that the data was loaded correctly
        self.assertIn("known_users", all_users)
        self.assertIn("TestUser", all_users["known_users"])
        self.assertIn("AnotherUser", all_users["known_users"])
        
        # Check specific user data
        test_user = all_users["known_users"]["TestUser"]
        self.assertEqual(test_user["name"], "TestUser")
        self.assertEqual(test_user["location"], "Sydney")
        self.assertIn("testing", test_user["likes"])
    
    def test_get_user_case_insensitive(self):
        """Test retrieving a user with case-insensitive name matching"""
        # Try to get user with different case
        user_data = self.user_model.get_user("testuser")
        
        # Check that the user was found despite case difference
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data["name"], "TestUser")
        self.assertEqual(user_data["location"], "Sydney")
    
    def test_get_user_nonexistent(self):
        """Test retrieving a non-existent user"""
        # Try to get non-existent user
        user_data = self.user_model.get_user("NonExistentUser")
        
        # Should return None for non-existent user
        self.assertIsNone(user_data)
    
    def test_set_and_save_current_user(self):
        """Test setting and saving the current user"""
        # Create a new user
        new_user = {
            "name": "NewUser",
            "location": "Melbourne",
            "profession": "Tester"
        }
        
        # Set as current user
        self.user_model.set_current_user(new_user)
        
        # Check that current user was set
        self.assertEqual(self.user_model.current_user, new_user)
        
        # Save current user
        self.user_model.save_current_user()
        
        # Reload to verify save
        all_users = self.user_model.load_all_users()
        self.assertIn("NewUser", all_users["known_users"])
        
        # Check that the saved data matches
        saved_user = all_users["known_users"]["NewUser"]
        self.assertEqual(saved_user["name"], "NewUser")
        self.assertEqual(saved_user["location"], "Melbourne")
        self.assertEqual(saved_user["profession"], "Tester")
    
    def test_update_user_info(self):
        """Test updating user information from extracted data"""
        # Set current user
        self.user_model.set_current_user({
            "name": "UpdateTest",
            "likes": ["coffee"],
            "dislikes": ["meetings"]
        })
        
        # Create extracted information
        extracted_info = [
            {"category": "profession", "value": "Engineer"},
            {"category": "likes", "value": "tea"},
            {"category": "likes", "value": "coffee"}, # Duplicate - should not add
            {"category": "dislikes", "value": "bugs"}
        ]
        
        # Update user info
        updates = self.user_model.update_user_info(extracted_info)
        
        # Check that updates were correctly reported
        self.assertEqual(len(updates), 3) # profession, likes:tea, dislikes:bugs
        
        # Check that the user data was updated correctly
        self.assertEqual(self.user_model.current_user["profession"], "Engineer")
        self.assertIn("tea", self.user_model.current_user["likes"])
        self.assertIn("coffee", self.user_model.current_user["likes"])
        self.assertEqual(len(self.user_model.current_user["likes"]), 2) # No duplicates
        self.assertIn("bugs", self.user_model.current_user["dislikes"])
    
    def test_update_user_info_empty_values(self):
        """Test updating user information with empty values"""
        # Set current user
        self.user_model.set_current_user({
            "name": "EmptyTest",
        })
        
        # Create extracted information with empty values
        extracted_info = [
            {"category": "profession", "value": ""},
            {"category": "likes", "value": " "},
            {"category": "location", "value": None}
        ]
        
        # Update user info
        updates = self.user_model.update_user_info(extracted_info)
        
        # Should not add empty values
        self.assertEqual(len(updates), 0)
        self.assertNotIn("profession", self.user_model.current_user)
        self.assertNotIn("likes", self.user_model.current_user)
        self.assertNotIn("location", self.user_model.current_user)
    
    def test_save_all_users(self):
        """Test saving all users to file"""
        # Create a modified user data set
        all_users = {
            "known_users": {
                "User1": {"name": "User1", "location": "Perth"},
                "User2": {"name": "User2", "profession": "Artist"}
            }
        }
        
        # Save all users
        self.user_model.save_all_users(all_users)
        
        # Reload to verify save
        reloaded = self.user_model.load_all_users()
        
        # Check that the saved data matches
        self.assertEqual(len(reloaded["known_users"]), 2)
        self.assertIn("User1", reloaded["known_users"])
        self.assertIn("User2", reloaded["known_users"])
        self.assertEqual(reloaded["known_users"]["User1"]["location"], "Perth")
        self.assertEqual(reloaded["known_users"]["User2"]["profession"], "Artist")

if __name__ == '__main__':
    unittest.main()
