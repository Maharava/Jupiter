import os
import datetime

class Logger:
    """Handles logging of chat sessions and messages"""
    
    def __init__(self, logs_folder="logs"):
        """Initialize logger with logs folder"""
        self.logs_folder = logs_folder
        self.current_log_file = None
        
        # Create logs folder if it doesn't exist
        os.makedirs(logs_folder, exist_ok=True)
    
    def start_new_log(self):
        """Create new log file for session"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.current_log_file = os.path.join(self.logs_folder, f"jupiter_chat_{timestamp}.log")
        
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Jupiter Chat Session: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
        
        return self.current_log_file
    
    def log_message(self, role, message):
        """Log message to current log file"""
        if self.current_log_file:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {role} {message}\n\n")
    
    def get_current_log_file(self):
        """Get the current log file path"""
        return self.current_log_file