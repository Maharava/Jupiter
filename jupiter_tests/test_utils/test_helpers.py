import os
import sys
import json
import datetime
import sqlite3
from unittest.mock import patch, MagicMock

# Import test environment
from .test_environment import TEST_ENV

class MockResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
        
    def json(self):
        return self.data

def get_mock_llm_response(message=None):
    """Get a mock LLM response based on content"""
    # Default response if no specific message pattern is found
    response = "I'm Jupiter, your AI assistant. How can I help you today?"
    
    # Check for patterns in message to provide appropriate responses
    if message:
        if "name" in message.lower() and "user" in message.lower():
            response = "Yes, I'll call you TestUser from now on."
        elif "time" in message.lower():
            now = datetime.datetime.now()
            response = f"The current time is {now.strftime('%I:%M %p')}."
        elif "calendar" in message.lower():
            response = "I see you're asking about your calendar. You have no upcoming events."
        elif "memory" in message.lower():
            response = "Based on our conversations, I remember you're from Sydney and you like testing and automation."
        elif "weather" in message.lower():
            response = "I don't have the ability to check the weather in real-time."
    
    return {"response": response}

class TestUserInterface:
    """Mock user interface for testing"""
    
    def __init__(self):
        self.messages = []
        self.inputs = []
        self.current_input_index = 0
        
    def print_jupiter_message(self, message):
        """Store Jupiter message"""
        self.messages.append({"role": "Jupiter", "message": message})
        
    def get_user_input(self, prefix="User"):
        """Return pre-defined user input"""
        if self.current_input_index < len(self.inputs):
            user_input = self.inputs[self.current_input_index]
            self.current_input_index += 1
            return user_input
        return "exit"  # Default to exit if no more inputs
    
    def set_inputs(self, inputs):
        """Set sequence of user inputs"""
        self.inputs = inputs
        self.current_input_index = 0
        
    def print_welcome(self):
        """Print welcome message"""
        self.messages.append({"role": "System", "message": "=== Jupiter Chat ==="})
    
    def print_exit_instructions(self):
        """Print exit instructions"""
        pass
    
    def handle_exit_command(self, user_input):
        """Check if user wants to exit"""
        return user_input.lower() in ['exit', 'quit']
    
    def exit_program(self):
        """Exit the program"""
        pass
        
    def set_status(self, status, is_busy=False):
        """Set status message"""
        self.messages.append({"role": "Status", "message": status, "is_busy": is_busy})
        
    def clear_chat(self):
        """Clear chat history"""
        pass

class TestLogger:
    """Mock logger for testing"""
    
    def __init__(self, logs_folder=None):
        self.logs = []
        self.logs_folder = logs_folder or os.path.join(TEST_ENV['temp_dir'], 'logs')
        self.current_log_file = None
        
    def start_new_log(self):
        """Create new log file for session"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.current_log_file = os.path.join(self.logs_folder, f"jupiter_chat_test_{timestamp}.log")
        
        # Create logs folder if it doesn't exist
        os.makedirs(self.logs_folder, exist_ok=True)
        
        # Create the log file
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Jupiter Chat Session: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
        
        return self.current_log_file
    
    def log_message(self, role, message):
        """Log message to current log file"""
        self.logs.append({"role": role, "message": message})
        
        if self.current_log_file:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {role} {message}\n\n")
    
    def get_current_log_file(self):
        """Get the current log file path"""
        return self.current_log_file

def create_test_calendar_db():
    """Create and populate a test calendar database"""
    # Create a test calendar database in the temp directory
    db_path = os.path.join(TEST_ENV['temp_dir'], 'test_calendar.db')
    
    # Connect to database (creates if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            all_day BOOLEAN DEFAULT 0,
            recurrence TEXT,
            privacy_level TEXT DEFAULT 'default',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create user_events association table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_events (
            user_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            is_owner BOOLEAN DEFAULT 1,
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            PRIMARY KEY (user_id, event_id)
        )
    ''')
    
    # Create reminders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            reminder_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            reminder_time TIMESTAMP NOT NULL,
            reminder_type TEXT DEFAULT 'notification',
            FOREIGN KEY (event_id) REFERENCES events(event_id)
        )
    ''')
    
    # Create some test events
    today = datetime.datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    tomorrow = today + datetime.timedelta(days=1)
    next_week = today + datetime.timedelta(days=7)
    
    # Event 1: Today's meeting
    cursor.execute('''
        INSERT INTO events (event_id, title, description, location, start_time, end_time, all_day)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        'test-event-1',
        'Team Meeting',
        'Weekly team status update',
        'Conference Room A',
        today.isoformat(),
        (today + datetime.timedelta(hours=1)).isoformat(),
        0
    ))
    
    # Associate with test user
    cursor.execute('''
        INSERT INTO user_events (user_id, event_id, is_owner)
        VALUES (?, ?, ?)
    ''', ('TestUser', 'test-event-1', 1))
    
    # Event 2: Tomorrow's all-day event
    cursor.execute('''
        INSERT INTO events (event_id, title, description, start_time, end_time, all_day)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        'test-event-2',
        'Company Workshop',
        'Annual planning workshop',
        tomorrow.replace(hour=0, minute=0, second=0).isoformat(),
        tomorrow.replace(hour=23, minute=59, second=59).isoformat(),
        1
    ))
    
    # Associate with test user
    cursor.execute('''
        INSERT INTO user_events (user_id, event_id, is_owner)
        VALUES (?, ?, ?)
    ''', ('TestUser', 'test-event-2', 1))
    
    # Event 3: Next week's meeting with reminder
    cursor.execute('''
        INSERT INTO events (event_id, title, description, location, start_time, end_time, all_day)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        'test-event-3',
        'Project Review',
        'Quarterly project status review',
        'Meeting Room B',
        next_week.isoformat(),
        (next_week + datetime.timedelta(hours=2)).isoformat(),
        0
    ))
    
    # Associate with test user
    cursor.execute('''
        INSERT INTO user_events (user_id, event_id, is_owner)
        VALUES (?, ?, ?)
    ''', ('TestUser', 'test-event-3', 1))
    
    # Add a reminder for this event
    reminder_time = next_week - datetime.timedelta(hours=1)
    cursor.execute('''
        INSERT INTO reminders (reminder_id, event_id, reminder_time, reminder_type)
        VALUES (?, ?, ?, ?)
    ''', (
        'test-reminder-1',
        'test-event-3',
        reminder_time.isoformat(),
        'notification'
    ))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    return db_path

def compare_user_data(user_data1, user_data2, only_check_fields=None):
    """
    Compare two user data dictionaries, optionally only checking specific fields
    """
    if only_check_fields:
        for field in only_check_fields:
            if field not in user_data1 or field not in user_data2:
                if field not in user_data1 and field not in user_data2:
                    continue  # Both don't have this field, so it's equal
                return False
            if user_data1[field] != user_data2[field]:
                return False
        return True
    else:
        return user_data1 == user_data2
