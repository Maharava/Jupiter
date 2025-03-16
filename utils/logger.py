import os
import datetime
import glob

class Logger:
    """Handles logging of chat sessions and messages"""
    
    def __init__(self, logs_folder="logs"):
        """Initialize logger with logs folder"""
        self.logs_folder = logs_folder
        self.current_log_file = None
        
        # Create logs folder if it doesn't exist
        os.makedirs(logs_folder, exist_ok=True)
        
        # Clean up any duplicate .txt logs
        self._clean_duplicate_logs()
    
    def _clean_duplicate_logs(self):
        """Remove any .txt log files that have matching .log files"""
        # Get lists of both types of log files
        log_files = set(glob.glob(os.path.join(self.logs_folder, "jupiter_chat_*.log")))
        txt_files = set(glob.glob(os.path.join(self.logs_folder, "jupiter_chat_*.txt")))
        
        # Find txt files with matching log files
        for txt_file in txt_files:
            base_name = os.path.splitext(txt_file)[0]
            log_file = base_name + ".log"
            
            if log_file in log_files:
                try:
                    os.remove(txt_file)
                    print(f"Removed duplicate log file: {txt_file}")
                except OSError as e:
                    print(f"Error removing duplicate log file {txt_file}: {e}")
    
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