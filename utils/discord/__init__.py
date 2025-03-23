# __init__.py
from .discord_client import DiscordClient
from .config import DiscordConfig

class DiscordModule:
    """Main integration point for Jupiter Discord functionality"""
    
    def __init__(self, chat_engine, user_data_manager, logger, config=None):
        from .config import DiscordConfig
        
        self.config = DiscordConfig(config)
        self.client = DiscordClient(
            chat_engine=chat_engine,
            user_data_manager=user_data_manager,
            logger=logger,
            config=self.config
        )
    
    def start(self):
        """Start the Discord bot"""
        self.client.start()
    
    def stop(self):
        """Stop the Discord bot"""
        self.client.stop()
    
    def is_running(self):
        """Check if bot is running"""
        return self.client.is_running