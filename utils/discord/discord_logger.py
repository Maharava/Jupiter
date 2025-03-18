# discord_logger.py

import logging

class DiscordLogger:
    """Specialized logger for Discord events"""
    
    def __init__(self, jupiter_logger=None):
        self.jupiter_logger = jupiter_logger
        
        # Set up Discord-specific logger
        self.logger = logging.getLogger('jupiter.discord')
        self.logger.setLevel(logging.INFO)
        
        # Add handler if not already added
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/discord.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_info(self, message):
        """Log info message"""
        self.logger.info(message)
        if self.jupiter_logger:
            self.jupiter_logger.log_message("Discord:", message)
    
    def log_error(self, message, exception=None):
        """Log error message"""
        if exception:
            self.logger.error(f"{message}: {str(exception)}")
        else:
            self.logger.error(message)
            
        if self.jupiter_logger:
            self.jupiter_logger.log_message("Discord Error:", message)
    
    def log_warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
        if self.jupiter_logger:
            self.jupiter_logger.log_message("Discord Warning:", message)