import os
import json
import threading
import logging

logger = logging.getLogger("jupiter.discord.user_mapper")

class UserMapper:
    """Maps Discord users to Jupiter users with ID-based tracking"""
    
    def __init__(self, user_data_manager, config):
        self.user_data_manager = user_data_manager
        self.config = config
        self.mapping_lock = threading.Lock()
        
        # We'll still maintain a local mapping cache for efficiency
        self.discord_id_map = {}
        
        # Load existing mapping if available
        self.mapping_file = config["user_mapping_file"]
        self._load_mapping()
    
    def get_jupiter_user(self, discord_user):
        """Get or create Jupiter user for Discord user"""
        discord_id = str(discord_user.id)
        
        # Use lock for thread safety
        with self.mapping_lock:
            # Check if we have a mapping in our cache
            if discord_id in self.discord_id_map:
                jupiter_id = self.discord_id_map[discord_id]
                
                # Get user from Jupiter
                jupiter_user = self.user_data_manager.get_user_by_id(jupiter_id)
                
                # If user found, update platform info and return
                if jupiter_user:
                    # Ensure platforms is initialized
                    if "platforms" not in jupiter_user:
                        jupiter_user["platforms"] = {}
                    
                    # Mark as seen on Discord
                    jupiter_user["platforms"]["discord"] = True
                    self.user_data_manager.set_current_user(jupiter_user)
                    self.user_data_manager.save_current_user()
                    return jupiter_user
            
            # Try to find by username if no direct mapping
            # This helps with backward compatibility and cross-platform recognition
            jupiter_user, user_id = self.user_data_manager.get_user_by_name(discord_user.name, "discord")
            
            if jupiter_user:
                # Update our cache
                self.discord_id_map[discord_id] = user_id
                self._save_mapping()
                return jupiter_user
        
        # No mapping or user not found, create new user
        return self._create_jupiter_user(discord_user)
    
    def _create_jupiter_user(self, discord_user):
        """Create a new Jupiter user based on Discord user"""
        discord_id = str(discord_user.id)
        
        # Use Discord username as Jupiter username
        jupiter_name = discord_user.name
        
        # Use lock for the entire operation
        with self.mapping_lock:
            # Create user in Jupiter
            user_data, actual_name = self.user_data_manager.identify_user(jupiter_name, "discord")
            
            # Store the mapping
            if 'user_id' in user_data:
                self.discord_id_map[discord_id] = user_data['user_id']
                self._save_mapping()
        
        return user_data
    
    def _load_mapping(self):
        """Load user mapping from file"""
        with self.mapping_lock:
            if os.path.exists(self.mapping_file):
                try:
                    with open(self.mapping_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Support new format
                        if isinstance(data, dict) and "discord_to_jupiter" in data:
                            self.discord_id_map = data["discord_to_jupiter"]
                        # Support old format for backward compatibility
                        elif isinstance(data, dict):
                            self.discord_id_map = data
                except json.JSONDecodeError:
                    # Invalid JSON, start with empty mapping
                    self.discord_id_map = {}
                    logger.warning(f"Invalid JSON in {self.mapping_file}, starting with empty mapping")
            else:
                # File doesn't exist, start with empty mapping
                self.discord_id_map = {}
    
    def _save_mapping(self):
        """Save user mapping to file"""
        with self.mapping_lock:
            try:
                # Create new format with metadata
                mapping_data = {
                    "discord_to_jupiter": self.discord_id_map,
                    "metadata": {
                        "last_updated": self._get_timestamp(),
                        "count": len(self.discord_id_map)
                    }
                }
                
                # Create directory if needed
                dir_name = os.path.dirname(self.mapping_file)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)
                    
                with open(self.mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(mapping_data, f, indent=4)
            except Exception as e:
                logger.error(f"Error saving Discord user mapping: {e}")
    
    def _get_timestamp(self):
        """Get current timestamp"""
        import time
        return int(time.time())

    def get_user_id_info(self, discord_user):
        """Get the Jupiter ID info for a Discord user"""
        discord_id = str(discord_user.id)
        
        # First check our mapping
        if discord_id in self.discord_id_map:
            jupiter_id = self.discord_id_map[discord_id]
            user_data = self.user_data_manager.get_user_by_id(jupiter_id)
            if user_data:
                return user_data
        
        # Try by name as fallback
        user, _ = self.user_data_manager.get_user_by_name(discord_user.name, "discord")
        return user