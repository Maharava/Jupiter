import json
import os

class UserModel:
    """Manages user data and operations"""
    
    def __init__(self, user_data_file):
        """Initialize with path to user data file"""
        self.user_data_file = user_data_file
        self.current_user = {}
    
    def load_all_users(self):
        """Load all user data from file"""
        if os.path.exists(self.user_data_file):
            with open(self.user_data_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        else:
            return {}
    
    def save_all_users(self, all_user_data):
        """Save all user data to file"""
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump(all_user_data, f, indent=4)
    
    def get_user(self, username):
        """Get a specific user's data"""
        all_users = self.load_all_users()
        
        if 'known_users' not in all_users:
            return None
            
        # Case-insensitive name lookup
        name_map = {name.lower(): name for name in all_users['known_users']}
        
        if username.lower() in name_map:
            actual_name = name_map[username.lower()]
            return all_users['known_users'][actual_name]
        
        return None
    
    def set_current_user(self, user_data):
        """Set the current user data"""
        self.current_user = user_data
    
    def save_current_user(self):
        """Save the current user data to file"""
        if not self.current_user or 'name' not in self.current_user:
            return
            
        all_user_data = self.load_all_users()
        
        # Make sure known_users exists
        if 'known_users' not in all_user_data:
            all_user_data['known_users'] = {}
        
        # Save the current user data
        all_user_data['known_users'][self.current_user['name']] = self.current_user
        
        # Save all user data
        self.save_all_users(all_user_data)
    
    def update_user_info(self, extracted_info):
        """Update current user with extracted information"""
        if not self.current_user or 'name' not in self.current_user:
            return []
        
        # Keep track of updates made
        updates = []
        
        for item in extracted_info:
            if 'category' in item and 'value' in item:
                category = item['category']
                value = item['value']
                
                # Skip empty values
                if not value or value.strip() == "":
                    continue
                
                # For lists (likes, dislikes, etc.)
                if category in ['likes', 'dislikes', 'interests', 'hobbies']:
                    if category not in self.current_user:
                        self.current_user[category] = []
                    
                    # Only add if not already present
                    if value not in self.current_user[category]:
                        self.current_user[category].append(value)
                        updates.append(f"{category}: {value}")
                else:
                    # For simple key-value pairs
                    # Only update if different from current value
                    if category not in self.current_user or self.current_user[category] != value:
                        self.current_user[category] = value
                        updates.append(f"{category}: {value}")
        
        # Save updates if any were made
        if updates:
            self.save_current_user()
            
        return updates