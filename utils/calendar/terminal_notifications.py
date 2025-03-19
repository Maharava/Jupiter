import logging
import platform
import os
import subprocess
import datetime

logger = logging.getLogger('jupiter.calendar.terminal_notifications')

# Try to import preferences
try:
    from .preferences_ui import get_preferences
except ImportError:
    # Create a dummy preferences getter
    def get_preferences():
        return None

class TerminalNotificationHandler:
    """
    Handler for calendar notifications in terminal mode
    """
    
    def __init__(self, terminal_ui=None):
        """
        Initialize terminal notification handler
        
        Args:
            terminal_ui: Terminal UI instance from Jupiter
        """
        self.terminal_ui = terminal_ui
        self.logger = logger
        self.use_native = False
        
        # Get preferences
        self.prefs = get_preferences()
        
        # Check if we can use native notifications
        self._check_native_notifications()
        
    def _check_native_notifications(self):
        """Check if native system notifications are available"""
        system = platform.system()
        
        if system == "Windows":
            # Check for PowerShell
            try:
                subprocess.run(
                    ["powershell", "-Command", "Get-Command -Name 'New-BurntToastNotification' -ErrorAction SilentlyContinue"],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                self.use_native = True
                logger.info("Windows native notifications available")
            except (subprocess.SubprocessError, FileNotFoundError):
                # BurntToast not installed or PowerShell not found
                logger.info("Windows native notifications not available")
                
        elif system == "Darwin":  # macOS
            # Check for terminal-notifier
            try:
                subprocess.run(
                    ["which", "terminal-notifier"],
                    capture_output=True,
                    timeout=1
                )
                self.use_native = True
                logger.info("macOS native notifications available")
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.info("macOS native notifications not available")
                
        elif system == "Linux":
            # Check for notify-send
            try:
                subprocess.run(
                    ["which", "notify-send"],
                    capture_output=True,
                    timeout=1
                )
                self.use_native = True
                logger.info("Linux native notifications available")
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.info("Linux native notifications not available")
        
    def handle_notification(self, notification):
        """
        Handle a calendar notification for terminal display
        
        Args:
            notification: Notification data dictionary
            
        Returns:
            bool: Success or failure
        """
        # Check if terminal notifications are enabled in preferences
        if self.prefs and not self.prefs.get_preference("terminal_notifications", True):
            logger.debug("Terminal notifications are disabled in preferences")
            return False
            
        try:
            # Try native notifications first
            if self.use_native and self._send_native_notification(notification):
                return True
                
            # Fall back to terminal UI
            return self._send_terminal_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error handling terminal notification: {e}")
            return False
            
    def _send_native_notification(self, notification):
        """
        Send notification using native system notification
        
        Args:
            notification: Notification data
            
        Returns:
            bool: Success or failure
        """
        try:
            system = platform.system()
            title = notification.get('title', 'Calendar Reminder')
            message = notification.get('message', '')
            
            if system == "Windows":
                # Use PowerShell BurntToast if available
                ps_script = f'''
                New-BurntToastNotification -Text "{title}", "{message}" -AppLogo Jupiter
                '''
                subprocess.run(
                    ["powershell", "-Command", ps_script],
                    capture_output=True,
                    timeout=2
                )
                return True
                
            elif system == "Darwin":  # macOS
                # Use terminal-notifier
                subprocess.run(
                    [
                        "terminal-notifier",
                        "-title", title,
                        "-message", message,
                        "-group", "Jupiter",
                    ],
                    capture_output=True,
                    timeout=2
                )
                return True
                
            elif system == "Linux":
                # Use notify-send
                subprocess.run(
                    [
                        "notify-send",
                        "--app-name=Jupiter",
                        "--urgency=normal",
                        title,
                        message
                    ],
                    capture_output=True,
                    timeout=2
                )
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error sending native notification: {e}")
            return False
            
    def _send_terminal_notification(self, notification):
        """
        Send notification using Jupiter's terminal UI
        
        Args:
            notification: Notification data
            
        Returns:
            bool: Success or failure
        """
        if not self.terminal_ui:
            return False
            
        title = notification.get('title', 'Calendar Reminder')
        message = notification.get('message', '')
        
        # Format a nice terminal notification
        notification_text = f"""
{'-' * 60}
{title}
{'-' * 60}
{message}
{'-' * 60}
"""
        
        # Send to terminal if we have access to the UI object
        if hasattr(self.terminal_ui, 'print_jupiter_message'):
            self.terminal_ui.print_jupiter_message(notification_text)
            return True
            
        # Fallback to stdout if no UI
        print(notification_text)
        return True


# Function to get a notification handler to register with the manager
def get_notification_handler(terminal_ui=None):
    """
    Get a terminal notification handler
    
    Args:
        terminal_ui: Terminal UI instance from Jupiter
        
    Returns:
        Tuple of (handler_name, handler_function)
    """
    handler = TerminalNotificationHandler(terminal_ui)
    return ("terminal", handler.handle_notification)