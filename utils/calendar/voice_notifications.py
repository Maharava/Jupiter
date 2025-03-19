import logging
import sys
import os

logger = logging.getLogger('jupiter.calendar.voice_notifications')

# Try to import preferences
try:
    from .preferences_ui import get_preferences
except ImportError:
    # Create a dummy preferences getter
    def get_preferences():
        return None

class VoiceNotificationHandler:
    """
    Handler for calendar notifications using text-to-speech
    """
    
    def __init__(self, tts_function=None):
        """
        Initialize voice notification handler
        
        Args:
            tts_function: Function to use for text-to-speech
        """
        self.tts_function = tts_function
        self.logger = logger
        
        # Get preferences
        self.prefs = get_preferences()
        
        # If no TTS function provided, try to import from Jupiter
        if not self.tts_function:
            self._import_jupiter_tts()
            
    def _import_jupiter_tts(self):
        """Import Jupiter's TTS functionality if available"""
        try:
            # Try to import Jupiter's TTS function
            from utils.piper import llm_speak
            self.tts_function = llm_speak
            logger.info("Using Jupiter's llm_speak for voice notifications")
            
        except ImportError:
            logger.warning("Could not import Jupiter's TTS functionality")
            self.tts_function = None
    
    def handle_notification(self, notification):
        """
        Handle a calendar notification with voice
        
        Args:
            notification: Notification data dictionary
            
        Returns:
            bool: Success or failure
        """
        # Check if voice notifications are enabled in preferences
        if self.prefs and not self.prefs.get_preference("voice_notifications", True):
            logger.debug("Voice notifications are disabled in preferences")
            return False
            
        if not self.tts_function:
            logger.warning("No TTS function available for voice notifications")
            return False
            
        try:
            # Speak the notification title and message
            title = notification.get('title', 'Calendar Reminder')
            message = notification.get('message', '')
            
            # Format a simple speech message
            speech_text = f"{title}. {message}"
            
            # Use TTS function
            self.tts_function(speech_text)
            logger.info(f"Voice notification delivered: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error delivering voice notification: {e}")
            return False


# Function to get a notification handler to register with the manager
def get_notification_handler():
    """
    Get a voice notification handler
    
    Returns:
        Tuple of (handler_name, handler_function)
    """
    handler = VoiceNotificationHandler()
    return ("voice", handler.handle_notification)