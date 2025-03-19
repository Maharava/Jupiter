import logging
import threading
import time
import sys
import traceback

from .notification_manager import NotificationManager
from .gui_notifications import get_notification_handler as get_gui_handler
from .terminal_notifications import get_notification_handler as get_terminal_handler
from .voice_notifications import get_notification_handler as get_voice_handler

logger = logging.getLogger('jupiter.calendar.daemon')

class CalendarDaemon:
    """
    Background daemon that manages calendar notifications
    
    This class is responsible for starting and managing the notification
    system and connecting it to appropriate delivery methods.
    """
    
    def __init__(self, calendar_manager=None):
        """
        Initialize the calendar daemon
        
        Args:
            calendar_manager: Calendar manager instance
        """
        self.notification_manager = NotificationManager(calendar_manager)
        self.initialized = False
        
    def initialize(self, gui_root=None, terminal_ui=None, enable_voice=True):
        """
        Initialize the notification system with available delivery methods
        
        Args:
            gui_root: Tkinter root window (for GUI mode)
            terminal_ui: Terminal UI instance (for terminal mode)
            enable_voice: Whether to enable voice notifications
            
        Returns:
            bool: Success or failure
        """
        if self.initialized:
            logger.warning("Calendar daemon already initialized")
            return True
            
        try:
            # Register available notification methods
            handlers_registered = 0
            
            # GUI notifications if in GUI mode
            if gui_root:
                gui_method, gui_handler = get_gui_handler(gui_root)
                self.notification_manager.register_delivery_method(gui_method, gui_handler)
                handlers_registered += 1
                logger.info("Registered GUI notification handler")
                
            # Terminal notifications if in terminal mode or as fallback
            if terminal_ui:
                term_method, term_handler = get_terminal_handler(terminal_ui)
                self.notification_manager.register_delivery_method(term_method, term_handler)
                handlers_registered += 1
                logger.info("Registered terminal notification handler")
                
            # Voice notifications if enabled
            if enable_voice:
                try:
                    voice_method, voice_handler = get_voice_handler()
                    self.notification_manager.register_delivery_method(voice_method, voice_handler)
                    handlers_registered += 1
                    logger.info("Registered voice notification handler")
                except Exception as e:
                    logger.warning(f"Failed to initialize voice notifications: {e}")
            
            # Start notification manager if we have at least one handler
            if handlers_registered > 0:
                self.notification_manager.start()
                self.initialized = True
                logger.info(f"Calendar daemon initialized with {handlers_registered} notification handlers")
                return True
            else:
                logger.warning("No notification handlers registered, daemon not started")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing calendar daemon: {e}")
            traceback.print_exc()
            return False
    
    def shutdown(self):
        """Shut down the calendar daemon"""
        if not self.initialized:
            return
            
        try:
            # Stop the notification manager
            self.notification_manager.stop()
            self.initialized = False
            logger.info("Calendar daemon shut down")
            
        except Exception as e:
            logger.error(f"Error shutting down calendar daemon: {e}")
            
    def is_initialized(self):
        """Check if the daemon is initialized"""
        return self.initialized


# Global daemon instance for easier access
_calendar_daemon = None

def initialize_calendar_daemon(gui_root=None, terminal_ui=None, enable_voice=True):
    """
    Initialize the global calendar daemon
    
    Args:
        gui_root: Tkinter root window (for GUI mode)
        terminal_ui: Terminal UI instance (for terminal mode)
        enable_voice: Whether to enable voice notifications
        
    Returns:
        bool: Success or failure
    """
    global _calendar_daemon
    
    try:
        if _calendar_daemon is None:
            _calendar_daemon = CalendarDaemon()
            
        return _calendar_daemon.initialize(gui_root, terminal_ui, enable_voice)
        
    except Exception as e:
        logger.error(f"Error initializing global calendar daemon: {e}")
        return False
        
def shutdown_calendar_daemon():
    """Shut down the global calendar daemon"""
    global _calendar_daemon
    
    if _calendar_daemon is not None:
        _calendar_daemon.shutdown()
        
def get_calendar_daemon():
    """Get the global calendar daemon instance"""
    global _calendar_daemon
    return _calendar_daemon
