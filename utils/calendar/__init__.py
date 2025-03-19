from .calendar_manager import CalendarManager
from .calendar_storage import CalendarStorage
from .calendar_commands import CalendarCommands
from .notification_manager import NotificationManager
from .daemon import initialize_calendar_daemon, shutdown_calendar_daemon, get_calendar_daemon

# Create a default instance of the calendar manager for easy access
default_manager = CalendarManager()

# Function to process calendar commands through the default manager
def process_calendar_command(user_id, command_text):
    """
    Process a calendar command using the default calendar manager
    
    Args:
        user_id (str): ID of the user issuing the command
        command_text (str): The command text to process
        
    Returns:
        str: Response message
    """
    command_handler = CalendarCommands(default_manager)
    return command_handler.process_command(user_id, command_text)