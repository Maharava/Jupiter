import unittest
import os
import tempfile
import datetime
import json
from pathlib import Path

from utils.calendar.calendar_storage import CalendarStorage
from utils.calendar.calendar_manager import CalendarManager
from utils.calendar.calendar_commands import CalendarCommands

class TestCalendarBasic(unittest.TestCase):
    """Basic tests for the calendar functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Initialize calendar storage with temp database
        self.storage = CalendarStorage(self.temp_db.name)
        
        # Initialize calendar manager with storage
        self.manager = CalendarManager(self.storage)
        
        # Initialize command handler
        self.commands = CalendarCommands(self.manager)
        
        # Test user ID
        self.user_id = "test_user"
    
    def tearDown(self):
        """Clean up test environment"""
        # Close and remove temp database
        try:
            os.unlink(self.temp_db.name)
        except (OSError, AttributeError):
            pass
    
    def test_create_event(self):
        """Test creating an event"""
        # Create a simple event
        event_id = self.manager.create_event(
            self.user_id,
            "Test Event",
            datetime.datetime.now().isoformat(),
            description="Test description"
        )
        
        # Check that event was created
        self.assertIsNotNone(event_id)
        
        # Get the event
        event = self.manager.get_event(self.user_id, event_id)
        
        # Check event data
        self.assertEqual(event['title'], "Test Event")
        self.assertEqual(event['description'], "Test description")
    
    def test_update_event(self):
        """Test updating an event"""
        # Create a simple event
        event_id = self.manager.create_event(
            self.user_id,
            "Test Event",
            datetime.datetime.now().isoformat()
        )
        
        # Update the event
        result = self.manager.update_event(
            self.user_id,
            event_id,
            title="Updated Event",
            description="Updated description"
        )
        
        # Check that update was successful
        self.assertTrue(result)
        
        # Get the event
        event = self.manager.get_event(self.user_id, event_id)
        
        # Check updated data
        self.assertEqual(event['title'], "Updated Event")
        self.assertEqual(event['description'], "Updated description")
    
    def test_delete_event(self):
        """Test deleting an event"""
        # Create a simple event
        event_id = self.manager.create_event(
            self.user_id,
            "Test Event",
            datetime.datetime.now().isoformat()
        )
        
        # Delete the event
        result = self.manager.delete_event(self.user_id, event_id)
        
        # Check that deletion was successful
        self.assertTrue(result)
        
        # Try to get the deleted event
        event = self.manager.get_event(self.user_id, event_id)
        
        # Check that event is gone
        self.assertIsNone(event)
    
    def test_get_upcoming_events(self):
        """Test getting upcoming events"""
        # Create events for today, tomorrow, and 10 days from now
        today = datetime.datetime.now()
        tomorrow = today + datetime.timedelta(days=1)
        future = today + datetime.timedelta(days=10)
        
        # Today event
        today_id = self.manager.create_event(
            self.user_id,
            "Today Event",
            today.isoformat()
        )
        
        # Tomorrow event
        tomorrow_id = self.manager.create_event(
            self.user_id,
            "Tomorrow Event",
            tomorrow.isoformat()
        )
        
        # Future event
        future_id = self.manager.create_event(
            self.user_id,
            "Future Event",
            future.isoformat()
        )
        
        # Get upcoming events (default 7 days)
        upcoming_events = self.manager.get_upcoming_events(self.user_id)
        
        # Check that we have today and tomorrow events but not future
        self.assertEqual(len(upcoming_events), 2)
        
        # Check event titles
        event_titles = [event['title'] for event in upcoming_events]
        self.assertIn("Today Event", event_titles)
        self.assertIn("Tomorrow Event", event_titles)
        self.assertNotIn("Future Event", event_titles)
        
        # Check with longer timeframe
        all_events = self.manager.get_upcoming_events(self.user_id, days=14)
        self.assertEqual(len(all_events), 3)
    
    def test_basic_command_parsing(self):
        """Test basic calendar command parsing"""
        # Test help command
        result = self.commands.process_command(self.user_id, "help")
        self.assertIn("Calendar Commands", result)
        
        # Test show events command
        result = self.commands.process_command(self.user_id, "show events")
        self.assertIn("No events found", result)
        
        # Test invalid command
        result = self.commands.process_command(self.user_id, "invalid command")
        self.assertIn("didn't understand", result)
    
    def test_add_event_command(self):
        """Test adding an event via command"""
        # Add an event for tomorrow
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        result = self.commands.process_command(self.user_id, f"add Meeting with Team on {tomorrow} at 2:00 PM")
        
        # Check that event was added
        self.assertIn("Added event", result)
        self.assertIn("Meeting with Team", result)
        
        # Check that event is in the database
        upcoming = self.manager.get_upcoming_events(self.user_id)
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0]['title'], "Meeting with Team")
    
    def test_show_events_command(self):
        """Test showing events via command"""
        # Add an event
        today = datetime.datetime.now()
        event_id = self.manager.create_event(
            self.user_id,
            "Important Meeting",
            (today + datetime.timedelta(hours=2)).isoformat()
        )
        
        # Show events for today
        result = self.commands.process_command(self.user_id, "show events for today")
        
        # Check that event is shown
        self.assertIn("Important Meeting", result)

if __name__ == '__main__':
    unittest.main()
