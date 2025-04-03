import os
import json
import datetime
import shutil
import threading

class LLMExchangeLogger:
    """
    Logs complete exchanges between users and LLM including full prompts and responses.
    Creates separate logs for each user that are deleted when the session ends.
    """
    
    def __init__(self, logs_folder):
        """Initialize the LLM exchange logger"""
        self.logs_folder = logs_folder
        self.exchange_logs_dir = os.path.join(logs_folder, "llm_exchanges")
        self.user_sessions = {}  # Maps user_id to log file path
        self.lock = threading.RLock()  # Thread-safe operations
        
        # Create exchange logs directory if it doesn't exist
        os.makedirs(self.exchange_logs_dir, exist_ok=True)
    
    def start_session(self, user_id, username):
        """
        Start a new logging session for a user
        Returns the path to the created log file
        """
        with self.lock:
            # Create user directory if it doesn't exist
            user_dir = os.path.join(self.exchange_logs_dir, user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            # Create timestamped log file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(user_dir, f"session_{timestamp}.jsonl")
            
            # Initialize log file with session metadata
            session_info = {
                "type": "session_start",
                "user_id": user_id,
                "username": username,
                "timestamp": datetime.datetime.now().isoformat(),
                "platform": "gui"  # Default, could be passed as parameter
            }
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(session_info) + "\n")
            
            # Store session file path
            self.user_sessions[user_id] = log_file
            
            return log_file
    
    def log_exchange(self, user_id, full_prompt, user_message, llm_response):
        """
        Log a complete exchange between user and LLM
        Returns True if successful, False otherwise
        """
        with self.lock:
            if user_id not in self.user_sessions:
                return False
            
            # Create exchange entry
            exchange = {
                "type": "exchange",
                "timestamp": datetime.datetime.now().isoformat(),
                "user_message": user_message,
                "full_prompt_to_llm": full_prompt,
                "llm_response": llm_response
            }
            
            # Append to log file
            try:
                with open(self.user_sessions[user_id], 'a', encoding='utf-8') as f:
                    f.write(json.dumps(exchange) + "\n")
                return True
            except Exception as e:
                print(f"Error logging LLM exchange: {e}")
                return False
    
    def end_session(self, user_id, delete_logs=True):
        """
        End a user session and optionally delete the logs
        Returns True if successful, False otherwise
        """
        with self.lock:
            if user_id not in self.user_sessions:
                return False
            
            # Write session end marker
            try:
                session_end = {
                    "type": "session_end",
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                with open(self.user_sessions[user_id], 'a', encoding='utf-8') as f:
                    f.write(json.dumps(session_end) + "\n")
            except Exception as e:
                print(f"Error finalizing session log: {e}")
            
            # Get log file path before removing from dict
            log_file = self.user_sessions[user_id]
            
            # Remove from active sessions
            del self.user_sessions[user_id]
            
            # Delete logs if requested
            if delete_logs and os.path.exists(log_file):
                try:
                    os.remove(log_file)
                    # Remove user directory if empty
                    user_dir = os.path.dirname(log_file)
                    if os.path.exists(user_dir) and not os.listdir(user_dir):
                        os.rmdir(user_dir)
                except Exception as e:
                    print(f"Error deleting log file: {e}")
                    return False
            
            return True
    
    def cleanup_all_sessions(self, delete_logs=True):
        """End all active sessions and optionally delete logs"""
        with self.lock:
            for user_id in list(self.user_sessions.keys()):
                self.end_session(user_id, delete_logs)