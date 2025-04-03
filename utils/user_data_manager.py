import os
import json
import uuid
import logging
import datetime

class UserDataManager:
    """Manages user data storage and retrieval with enhanced identity tracking"""
    
    def __init__(self, data_folder, config=None):
        """Initialize the user data manager"""
        self.data_folder = data_folder
        self.config = config
        self.user_data_file = os.path.join(data_folder, "user_data.json")
        self.current_user = None
        self.current_user_id = None
        
        # Create data folder if it doesn't exist
        os.makedirs(data_folder, exist_ok=True)
        
        # Initialize user data if it doesn't exist
        if not os.path.exists(self.user_data_file):
            self.initialize_user_data()
    
    def initialize_user_data(self):
        """Create initial user data file"""
        initial_data = {
            "users": {},
            "name_map": {},
            "platform_map": {}
        }
        self.save_user_data(initial_data)
    
    def load_user_data(self):
        """Load user data from file"""
        try:
            with open(self.user_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create new user data file if it doesn't exist
            self.initialize_user_data()
            return self.load_user_data()
        except json.JSONDecodeError:
            logging.error(f"Failed to parse user data file: {self.user_data_file}")
            # Create backup of corrupted file
            backup_file = f"{self.user_data_file}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                os.rename(self.user_data_file, backup_file)
                logging.info(f"Created backup of corrupted user data: {backup_file}")
            except Exception as e:
                logging.error(f"Failed to create backup of corrupted user data: {e}")
            
            # Create new user data file
            self.initialize_user_data()
            return self.load_user_data()
    
    def save_user_data(self, data):
        """Save user data to file"""
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    
    def get_user(self, username, platform="all"):
        """Get user by username, checking across all platforms and name history"""
        data = self.load_user_data()
        username_lower = username.lower()
        
        # Check name map first (direct lookup)
        if username_lower in data.get("name_map", {}):
            user_id = data["name_map"][username_lower]
            if user_id in data["users"]:
                return data["users"][user_id]
        
        # If specific platform is requested, check that first
        if platform != "all":
            platform_key = f"{platform}:{username_lower}"
            if platform_key in data.get("platform_map", {}):
                user_id = data["platform_map"][platform_key]
                if user_id in data["users"]:
                    return data["users"][user_id]
        
        # Check all platforms if not found or if platform="all"
        for p in ["gui", "discord", "terminal"]:
            if platform != "all" and p == platform:
                continue  # Already checked this platform
                
            platform_key = f"{p}:{username_lower}"
            if platform_key in data.get("platform_map", {}):
                user_id = data["platform_map"][platform_key]
                if user_id in data["users"]:
                    return data["users"][user_id]
        
        # Check user IDs directly (in case someone tries to link by ID)
        if username in data.get("users", {}):
            return data["users"][username]
        
        # Check name history in all users
        for user_id, user_data in data["users"].items():
            if "name_history" in user_data:
                for historical_name in user_data["name_history"]:
                    if historical_name.lower() == username_lower:
                        return user_data
        
        # User not found
        return None
    
    def create_user(self, user_data, platform="gui"):
        """Create a new user"""
        if "name" not in user_data:
            user_data["name"] = "User"
        
        # Generate unique user ID
        user_id = str(uuid.uuid4())
        
        # Add platforms data
        if "platforms" not in user_data:
            user_data["platforms"] = {}
        user_data["platforms"][platform] = True
        
        # Add created timestamp
        user_data["created_at"] = datetime.datetime.now().isoformat()
        
        # Save user to database
        data = self.load_user_data()
        data["users"][user_id] = user_data
        
        # Update name map
        username_lower = user_data["name"].lower()
        data["name_map"][username_lower] = user_id
        
        # Update platform map
        platform_key = f"{platform}:{username_lower}"
        data["platform_map"][platform_key] = user_id
        
        self.save_user_data(data)
        return user_id
    
    def update_user(self, user_id, updated_user_data):
        """Update a user with name history tracking"""
        data = self.load_user_data()
        
        if user_id in data["users"]:
            # If name is changing, store the old name in history
            if "name" in updated_user_data:
                old_name = data["users"][user_id].get("name")
                new_name = updated_user_data["name"]
                
                if old_name and old_name != new_name:
                    # Initialize name_history if needed
                    if "name_history" not in data["users"][user_id]:
                        data["users"][user_id]["name_history"] = []
                    
                    # Add old name to history if not already there
                    if old_name not in data["users"][user_id]["name_history"]:
                        data["users"][user_id]["name_history"].append(old_name)
                    
                    # Update name map - remove old mapping
                    old_name_lower = old_name.lower()
                    if old_name_lower in data.get("name_map", {}) and data["name_map"][old_name_lower] == user_id:
                        data["name_map"].pop(old_name_lower, None)
                    
                    # Add new mapping
                    new_name_lower = new_name.lower()
                    data["name_map"][new_name_lower] = user_id
                    
                    # Update platform mappings
                    if "platforms" in data["users"][user_id]:
                        for platform in data["users"][user_id]["platforms"]:
                            old_platform_key = f"{platform}:{old_name_lower}"
                            if old_platform_key in data.get("platform_map", {}):
                                data["platform_map"].pop(old_platform_key, None)
                            
                            new_platform_key = f"{platform}:{new_name_lower}"
                            data["platform_map"][new_platform_key] = user_id
            
            # Update user data
            data["users"][user_id].update(updated_user_data)
            
            # Save changes
            self.save_user_data(data)
            return True
        else:
            logging.warning(f"Attempted to update non-existent user ID: {user_id}")
            return False
    
    def link_accounts(self, primary_user_id, secondary_user_id):
        """Link two accounts, merging data to the primary account"""
        data = self.load_user_data()
        
        if primary_user_id not in data["users"] or secondary_user_id not in data["users"]:
            return False
        
        primary_user = data["users"][primary_user_id]
        secondary_user = data["users"][secondary_user_id]
        
        # Merge platforms
        if "platforms" not in primary_user:
            primary_user["platforms"] = {}
        
        if "platforms" in secondary_user:
            for platform, value in secondary_user["platforms"].items():
                primary_user["platforms"][platform] = value
        
        # Initialize name history if needed
        if "name_history" not in primary_user:
            primary_user["name_history"] = []
        
        # Add secondary user's name to history
        secondary_name = secondary_user.get("name")
        if secondary_name and secondary_name not in primary_user["name_history"] and secondary_name != primary_user.get("name"):
            primary_user["name_history"].append(secondary_name)
        
        # Add secondary user's name history to primary
        if "name_history" in secondary_user:
            for name in secondary_user["name_history"]:
                if name not in primary_user["name_history"] and name != primary_user.get("name"):
                    primary_user["name_history"].append(name)
        
        # Merge other important user data
        for key in ["likes", "dislikes", "preferences", "facts", "background", "conversations"]:
            if key in secondary_user and key not in primary_user:
                primary_user[key] = secondary_user[key]
            elif key in secondary_user and key in primary_user and isinstance(primary_user[key], list):
                # For list fields, combine unique values
                combined = primary_user[key] + [item for item in secondary_user[key] if item not in primary_user[key]]
                primary_user[key] = combined
        
        # Update platform mappings to point to primary user
        for platform, platform_data in data.get("platform_map", {}).items():
            for name, user_id in list(platform_data.items()):
                if user_id == secondary_user_id:
                    data["platform_map"][platform][name] = primary_user_id
        
        # Update name mappings to point to primary user
        for name, user_id in list(data.get("name_map", {}).items()):
            if user_id == secondary_user_id:
                data["name_map"][name] = primary_user_id
        
        # Delete secondary user
        del data["users"][secondary_user_id]
        
        # Save changes
        self.save_user_data(data)
        return True