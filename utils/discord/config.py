class DiscordConfig:
    """Manages Discord module configuration"""
    
    DEFAULT_CONFIG = {
        "token": "",
        "allowed_servers": [],  # Empty list = all servers
        "allowed_channels": [], # Empty list = all channels
        "observation_timeout": 300,  # How long Jupiter observes before becoming inactive
        "name_variations": ["jupiter", "jup"],  # Names that trigger attention
        "response_threshold": 0.7,  # Confidence threshold for responding
        "max_history_per_channel": 50,  # Max messages to keep in context
        "user_mapping_file": "discord_users.json"
    }
    
    def __init__(self, config_dict=None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config_dict:
            self.config.update(config_dict)
        
        # Check for token in environment variable
        import os
        env_token = os.environ.get("JUPITER_DISCORD_TOKEN")
        if env_token:
            self.config["token"] = env_token
        
        self.validate()
    
    def validate(self):
        """Ensure config has required fields"""
        if not self.config.get("token"):
            raise ValueError("Discord token is required")
    
    def __getitem__(self, key):
        return self.config.get(key)