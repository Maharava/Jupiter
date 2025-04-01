# __init__.py - Discord module entry point
from .discord_client import JupiterDiscordClient
from .config import DiscordConfig

class DiscordModule:
    """Main integration point for Jupiter Discord functionality"""
    
    def __init__(self, chat_engine, user_data_manager, logger, config=None):
        """Initialize Discord module"""
        self.config = DiscordConfig(config)
        self.client = JupiterDiscordClient(
            chat_engine=chat_engine,
            user_data_manager=user_data_manager,
            config=self.config
        )
        self.logger = logger
    
    def start(self):
        """Start the Discord bot in a non-blocking way"""
        import threading
        
        def run_discord_client():
            try:
                self.logger.log_message("System:", "Starting Discord integration")
                self.client.start()
            except Exception as e:
                self.logger.log_message("System Error:", f"Discord integration failed: {str(e)}")
        
        # Start client in a separate thread
        discord_thread = threading.Thread(
            target=run_discord_client,
            daemon=True,
            name="DiscordThread"
        )
        discord_thread.start()
    
    def stop(self):
        """Stop the Discord bot"""
        self.logger.log_message("System:", "Stopping Discord integration")
        self.client.stop()
    
    @property
    def is_running(self):
        """Check if bot is running"""
        return self.client.is_running