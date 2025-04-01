import os
import logging

class DiscordConfig:
    """Configuration for Jupiter's Discord integration"""
    
    DEFAULT_CONFIG = {
        "token": "",                    # Discord bot token
        "allowed_servers": [],          # Empty list = all servers
        "allowed_channels": [],         # Empty list = all channels
        "observation_timeout": 300,     # How long Jupiter observes a channel (seconds)
        "name_variations": ["jupiter", "jup"],  # Names that trigger attention
    }
    
    def __init__(self, config_dict=None):
        """Initialize configuration with defaults and overrides"""
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Apply provided config
        if config_dict:
            self.config.update(config_dict)
        
        # Check for token in environment variable
        env_token = os.environ.get("JUPITER_DISCORD_TOKEN")
        if env_token:
            self.config["token"] = env_token
        
        self.validate()
    
    def validate(self):
        """Ensure config has required fields"""
        if not self.config.get("token"):
            logging.error("Discord token is required but not provided")
            return False
        return True
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
        
    def __getitem__(self, key):
        """Allow dictionary-style access to config values"""
        return self.config.get(key)