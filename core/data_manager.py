import os
import json

class DataManager:
    """Manages user data storage and extraction."""
    
    def __init__(self, user_data_file):
        """Initialize data manager with path to user data file"""
        self.user_data_file = user_data_file
        
        # Create empty user data file if it doesn't exist
        if not os.path.exists(user_data_file):
            with open(user_data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def load_user_data(self):
        """Load user data from file"""
        if os.path.exists(self.user_data_file):
            with open(self.user_data_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        else:
            return {}
    
    def save_user_data(self, data):
        """Save user data to file"""
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    
    def identify_user(self, username):
        """Identify a user by username"""
        data = self.load_user_data()
        
        # Make sure known_users exists
        if 'known_users' not in data:
            data['known_users'] = {}
        
        # Check if user exists (case insensitive)
        name_map = {name.lower(): name for name in data['known_users']}
        
        if username.lower() in name_map:
            # Use the proper capitalization of the name
            actual_name = name_map[username.lower()]
            return data['known_users'][actual_name], actual_name
        
        # Create new user
        new_user = {'name': username}
        data['known_users'][username] = new_user
        self.save_user_data(data)
        
        return new_user, username