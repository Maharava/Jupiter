import os
import json

class UserMapper:
    """Maps Discord users to Jupiter users"""
    
    def __init__(self, user_model, config):
        self.user_model = user_model
        self.config = config
        self.mapping = {}
        
        # Load existing mapping if available
        self.mapping_file = config["user_mapping_file"]
        self._load_mapping()
    
    def get_jupiter_user(self, discord_user):
        """Get or create Jupiter user for Discord user"""
        discord_id = str(discord_user.id)
        
        # Check if mapping exists
        if discord_id in self.mapping:
            jupiter_name = self.mapping[discord_id]
            
            # Get user from Jupiter
            jupiter_user = self.user_model.get_user(jupiter_name)
            
            # If user found, return it
            if jupiter_user:
                return jupiter_user
        
        # No mapping or user not found, create new user
        return self._create_jupiter_user(discord_user)
    
    def _create_jupiter_user(self, discord_user):
        """Create a new Jupiter user based on Discord user"""
        discord_id = str(discord_user.id)
        
        # Use Discord username as Jupiter username
        jupiter_name = discord_user.name
        
        # Check if this name exists
        existing_user = self.user_model.get_user(jupiter_name)
        
        if existing_user:
            # Add discriminator if name exists
            jupiter_name = f"{discord_user.name}#{discord_user.discriminator}"
        
        # Create user data
        user_data = {
            'name': jupiter_name,
            'discord_id': discord_id,
            'location': None,
            'likes': [],
            'dislikes': [],
            'interests': []
        }
        
        # Set as current user and save
        self.user_model.set_current_user(user_data)
        self.user_model.save_current_user()
        
        # Update mapping
        self.mapping[discord_id] = jupiter_name
        self._save_mapping()
        
        return user_data
    
    def _load_mapping(self):
        """Load user mapping from file"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    self.mapping = json.load(f)
            except json.JSONDecodeError:
                # Invalid JSON, start with empty mapping
                self.mapping = {}
        else:
            # File doesn't exist, start with empty mapping
            self.mapping = {}
    
    def _save_mapping(self):
        """Save user mapping to file"""
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mapping, f, indent=4)
        except Exception as e:
            print(f"Error saving Discord user mapping: {e}")