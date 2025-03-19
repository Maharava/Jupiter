import os
import sys
import unittest
import tempfile
import datetime
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter modules
from core.chat_engine import ChatEngine
from models.user_model import UserModel
from utils.calendar.calendar_manager import CalendarManager
from utils.calendar.calendar_storage import CalendarStorage
from utils.calendar.calendar_commands import CalendarCommands
from utils.calendar.notification_manager import NotificationManager
from utils.calendar.formats.ical import ICalHandler
from utils.calendar.formats.csv_handler import CSVHandler

# Import test utilities
from test_utils.test_environment import setup_test_environment, cleanup_test_environment
from test_utils.test_helpers import TestUserInterface, TestLogger, create_test_calendar_db
from mocks.mock_llm import MockLLMClient

class TestCalendarWorkflow(unittest.TestCase):
    """
    Test complete workflows for calendar functionality.
    
    This covers:
    - Creating events with natural language commands
    - Querying upcoming events
    - Managing calendar notifications
    - Import/export calendar data
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        cls.test_env = setup_test_environment()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up test components for each test"""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.user_data_file = os.path.join(self.temp_dir, 'test_user_data.json')
        self.prompt_folder = os.path.join(self.temp_dir, "prompts")
        self.logs_folder = os.path.join(self.temp_dir, "logs")
        self.export_dir = os.path.join(self.temp_dir, "exports")
        
        # Create folders
        os.makedirs(self.prompt_folder, exist_ok=True)
        os.makedirs(self.logs_folder, exist_ok=True)
        os.makedirs(self.export_dir, exist_ok=True)
        
        # Create user data file
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump({"known_users": {"CalendarUser": {"name": "CalendarUser"}}}, f)
        
        # Create system prompt file
        with open(os.path.join(self.prompt_folder, "system_prompt.txt"), 'w', encoding='utf-8') as f:
            f.write("I am Jupiter, an AI assistant. I'm helpful and friendly.")
        
        # Create a calendar database with test data
        self.db_path = create_test_calendar_db()
        
        # Create calendar components
        self.storage = CalendarStorage(self.db_path)
        self.calendar_manager = CalendarManager(self.storage)
        self.calendar_commands = CalendarCommands(self.calendar_manager)
        
        # Create other components
        self.user_model = UserModel(self.user_data_file)
        self.user_model.set_current_user({"name": "CalendarUser"})
        self.llm_client = MockLLMClient()
        self.logger = TestLogger(logs_folder=self.logs_folder)
        self.ui = TestUserInterface()
        
        # Set up config
        self.config = {
            "llm": {
                "provider": "ollama",
                "api_url": "http://localhost:11434",
                "default_model": "gemma3",
                "chat_temperature": 0.7,
                "extraction_temperature": 0.2,
                "token_limit": 8192
            },
            "paths": {
                "prompt_folder": self.prompt_folder,
                "logs_folder": self.logs_folder,
                "user_data_file": self.user_data_file
            },
            "ui": {
                "jupiter_color": "yellow",
                "user_color": "magenta"
            },
            "calendar": {
                "enable_notifications": True,
                "notification_check_interval": 1,
                "prompt_detail_level": "normal",
                "default_reminder_minutes": 15
            }
        }
        
        # Create a ChatEngine with our components
        self.chat_engine = ChatEngine(
            llm_client=self.llm_client,
            user_model=self.user_model,
            logger=self.logger,
            ui=self.ui,
            config=self.config,
            test_mode=True
        )
        
        # Setup calendar command processing
        import utils.calendar
        self.original_default_manager = utils.calendar.default_manager
        utils.calendar.default_manager = self.calendar_manager
    
    def tearDown(self):
        """Clean up after each test"""
        # Restore original calendar manager
        import utils.calendar
        utils.calendar.default_manager = self.original_default_manager
        
        # Remove temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # Remove database file
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_adding_event_workflow(self):
        """Test the complete workflow for adding and viewing events"""
        # All commands
        commands = [
            "/calendar add Meeting with client on tomorrow at 10:00 AM at Conference Room A",
            "/calendar add Lunch with team on tomorrow at 12:30 PM at Cafe",
            "/calendar show events for tomorrow",
            "/calendar help"
        ]
        
        results = []
        for command in commands:
            response = self.chat_engine.handle_user_commands(command)
            results.append(response)
        
        # Check that the first event was added successfully
        self.assertIn("Added event", results[0])
        self.assertIn("Meeting with client", results[0])
        self.assertIn("Conference Room A", results[0])
        
        # Check that the second event was added successfully
        self.assertIn("Added event", results[1])
        self.assertIn("Lunch with team", results[1])
        self.assertIn("Cafe", results[1])
        
        # Check that both events appear in the show events response
        self.assertIn("Meeting with client", results[2])
        self.assertIn("Lunch with team", results[2])
        self.assertIn("Conference Room A", results[2])
        self.assertIn("Cafe", results[2])
        
        # Verify events were actually added to the database
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
        events = self.calendar_manager.get_events_by_date("CalendarUser", tomorrow)
        
        # Should have the two new events plus the Company Workshop from test data
        self.assertEqual(len(events), 3)
        titles = [event["title"] for event in events]
        self.assertIn("Meeting with client", titles)
        self.assertIn("Lunch with team", titles)
        self.assertIn("Company Workshop", titles)  # From test data
    
    def test_natural_language_date_parsing(self):
        """Test adding events with various natural language date expressions"""
        # Natural language date expressions
        date_expressions = [
            "today at 3:00 PM",
            "tomorrow at 9:30 AM",
            "next Monday at 10:00 AM",
            "next week at 2:00 PM",
            "December 25 at 12:00 PM",
            "2023-12-31 at 11:59 PM"
        ]
        
        # Add events with each date expression
        for i, date_expr in enumerate(date_expressions):
            command = f"/calendar add Test Event {i+1} on {date_expr}"
            response = self.chat_engine.handle_user_commands(command)
            
            # Check that event was added
            self.assertIn("Added event", response)
            self.assertIn(f"Test Event {i+1}", response)
        
        # Get all events to check if they were added correctly
        all_events_response = self.chat_engine.handle_user_commands("/calendar show events")
        
        # Check that all events appear in the response
        for i in range(len(date_expressions)):
            self.assertIn(f"Test Event {i+1}", all_events_response)
    
    def test_export_import_workflow(self):
        """Test exporting and importing calendar data"""
        # Add a couple of events
        self.chat_engine.handle_user_commands("/calendar add Export Test 1 on tomorrow at 9:00 AM")
        self.chat_engine.handle_user_commands("/calendar add Export Test 2 on tomorrow at 3:00 PM")
        
        # Export to ICS format
        ics_path = os.path.join(self.export_dir, "test_export.ics")
        export_response = self.chat_engine.handle_user_commands(f"/calendar export calendar to {ics_path}")
        
        # Check that export was successful
        self.assertIn("Successfully exported", export_response)
        self.assertTrue(os.path.exists(ics_path))
        
        # Export to CSV format
        csv_path = os.path.join(self.export_dir, "test_export.csv")
        export_response = self.chat_engine.handle_user_commands(f"/calendar export calendar as {csv_path}")
        
        # Check that export was successful
        self.assertIn("Successfully exported", export_response)
        self.assertTrue(os.path.exists(csv_path))
        
        # Create a new calendar storage for import testing
        import_db_path = os.path.join(self.temp_dir, "import_calendar.db")
        import_storage = CalendarStorage(import_db_path)
        import_manager = CalendarManager(import_storage)
        
        # Replace default calendar manager with the import one
        import utils.calendar
        utils.calendar.default_manager = import_manager
        
        # Import from ICS file
        import_response = self.chat_engine.handle_user_commands(f"/calendar import events from {ics_path}")
        
        # Check that import was successful
        self.assertIn("Successfully imported", import_response)
        
        # Check that events were imported
        events_response = self.chat_engine.handle_user_commands("/calendar show events")
        self.assertIn("Export Test 1", events_response)
        self.assertIn("Export Test 2", events_response)
        
        # Restore original calendar manager
        utils.calendar.default_manager = self.calendar_manager
    
    def test_notification_workflow(self):
        """Test the notification workflow"""
        # Create a notification manager for testing
        notification_manager = NotificationManager(self.calendar_manager)
        
        # Register a test notification handler
        notifications_received = []
        
        def test_notification_handler(notification):
            notifications_received.append(notification)
            return True
        
        notification_manager.register_delivery_method("test", test_notification_handler)
        
        # Add an event with a reminder in the past (so it triggers immediately)
        now = datetime.datetime.now()
        past_reminder = now - datetime.timedelta(minutes=5)
        
        # Create event with a reminder time in the past
        event_id = self.calendar_manager.create_event(
            "CalendarUser",
            "Notification Test",
            now.isoformat(),
            end_time=(now + datetime.timedelta(hours=1)).isoformat()
        )
        
        # Add reminder directly to database
        import uuid
        reminder_id = str(uuid.uuid4())
        conn = self.storage._get_connection()
        conn.execute(
            "INSERT INTO reminders (reminder_id, event_id, reminder_time, reminder_type) VALUES (?, ?, ?, ?)",
            (reminder_id, event_id, past_reminder.isoformat(), "notification")
        )
        conn.commit()
        conn.close()
        
        # Process notifications
        notification_manager._check_reminders()
        notification_manager._process_queue()
        
        # Check that the notification was processed
        self.assertEqual(len(notifications_received), 1)
        self.assertEqual(notifications_received[0]["title"], "Reminder: Notification Test")
        
        # Check that the reminder was marked as delivered
        reminders = self.storage.get_pending_reminders(current_time=past_reminder.isoformat())
        self.assertEqual(len(reminders), 0)
    
    def test_schedule_analysis(self):
        """Test analyzing schedule density"""
        # Get initial schedule density
        density_before = self.calendar_manager.get_schedule_density("CalendarUser")
        
        # Add several events to make the schedule busy
        for i in range(5):
            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
            tomorrow = tomorrow.replace(hour=9 + i*2, minute=0, second=0, microsecond=0)
            
            self.calendar_manager.create_event(
                "CalendarUser",
                f"Busy Event {i+1}",
                tomorrow.isoformat(),
                end_time=(tomorrow + datetime.timedelta(hours=1, minutes=30)).isoformat()
            )
        
        # Get density after adding events
        density_after = self.calendar_manager.get_schedule_density("CalendarUser")
        
        # Check that density increased
        self.assertGreater(density_after, density_before)
        
        # With multiple long events, density should be fairly high
        self.assertGreater(density_after, 0.5)

if __name__ == '__main__':
    unittest.main()
