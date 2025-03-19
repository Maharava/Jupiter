import os
import sys
import unittest
import datetime
import json
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Jupiter calendar modules
from utils.calendar.calendar_storage import CalendarStorage
from utils.calendar.calendar_manager import CalendarManager
from utils.calendar.calendar_commands import CalendarCommands
from utils.calendar.prompt_enhancer import PromptEnhancer
from utils.calendar.notification_manager import NotificationManager
from utils.calendar.formats.ical import ICalHandler
from utils.calendar.formats.csv_handler import CSVHandler

# Import test utilities
from test_utils.test_environment import setup_test_environment, cleanup_test_environment
from test_utils.test_helpers import create_test_calendar_db

class TestCalendarStorage(unittest.TestCase):
    """Test the CalendarStorage class"""
    
    def setUp(self):
        """Set up a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.storage = CalendarStorage(self.temp_db.name)
    
    def tearDown(self):
        """Clean up the temporary database after each test"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_add_event(self):
        """Test adding an event to the calendar"""
        # Create a test event
        event_data = {
            'title': 'Test Event',
            'description': 'This is a test event',
            'location': 'Test Location',
            'start_time': datetime.datetime.now().isoformat(),
            'end_time': (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat(),
            'all_day': False
        }
        
        # Add the event
        event_id = self.storage.add_event(event_data, 'test_user')
        
        # Check that the event was added successfully
        self.assertIsNotNone(event_id)
        
        # Get the event to verify
        event = self.storage.get_event(event_id, 'test_user')
        
        # Check that the event data matches
        self.assertEqual(event['title'], 'Test Event')
        self.assertEqual(event['description'], 'This is a test event')
        self.assertEqual(event['location'], 'Test Location')
        self.assertFalse(event['all_day'])
    
    def test_update_event(self):
        """Test updating an event"""
        # Create a test event
        event_data = {
            'title': 'Original Title',
            'description': 'Original description',
            'start_time': datetime.datetime.now().isoformat()
        }
        
        # Add the event
        event_id = self.storage.add_event(event_data, 'test_user')
        
        # Update the event
        update_data = {
            'title': 'Updated Title',
            'description': 'Updated description'
        }
        
        result = self.storage.update_event(event_id, update_data, 'test_user')
        
        # Check that the update was successful
        self.assertTrue(result)
        
        # Get the updated event
        event = self.storage.get_event(event_id, 'test_user')
        
        # Check that the event data was updated
        self.assertEqual(event['title'], 'Updated Title')
        self.assertEqual(event['description'], 'Updated description')
    
    def test_delete_event(self):
        """Test deleting an event"""
        # Create a test event
        event_data = {
            'title': 'Event to Delete',
            'start_time': datetime.datetime.now().isoformat()
        }
        
        # Add the event
        event_id = self.storage.add_event(event_data, 'test_user')
        
        # Delete the event
        result = self.storage.delete_event(event_id, 'test_user')
        
        # Check that the deletion was successful
        self.assertTrue(result)
        
        # Try to get the deleted event
        event = self.storage.get_event(event_id, 'test_user')
        
        # Event should no longer exist
        self.assertIsNone(event)
    
    def test_get_upcoming_events(self):
        """Test getting upcoming events"""
        # Create test events at different times
        now = datetime.datetime.now()
        
        # Event 1: Today
        event1 = {
            'title': 'Today Event',
            'start_time': now.isoformat()
        }
        
        # Event 2: Tomorrow
        event2 = {
            'title': 'Tomorrow Event',
            'start_time': (now + datetime.timedelta(days=1)).isoformat()
        }
        
        # Event 3: Next week (outside default 7-day window)
        event3 = {
            'title': 'Next Week Event',
            'start_time': (now + datetime.timedelta(days=10)).isoformat()
        }
        
        # Add the events
        event_id1 = self.storage.add_event(event1, 'test_user')
        event_id2 = self.storage.add_event(event2, 'test_user')
        event_id3 = self.storage.add_event(event3, 'test_user')
        
        # Get upcoming events (default 7 days)
        events = self.storage.get_upcoming_events('test_user')
        
        # Check that only today and tomorrow events are included
        self.assertEqual(len(events), 2)
        titles = [event['title'] for event in events]
        self.assertIn('Today Event', titles)
        self.assertIn('Tomorrow Event', titles)
        self.assertNotIn('Next Week Event', titles)
        
        # Get upcoming events with extended window
        events_extended = self.storage.get_upcoming_events('test_user', days=14)
        
        # Check that all events are included with extended window
        self.assertEqual(len(events_extended), 3)
        titles = [event['title'] for event in events_extended]
        self.assertIn('Next Week Event', titles)
    
    def test_is_time_available(self):
        """Test checking if a time is available"""
        # Create a test event
        now = datetime.datetime.now()
        start_time = now.replace(hour=14, minute=0, second=0, microsecond=0)
        end_time = start_time + datetime.timedelta(hours=2)
        
        event_data = {
            'title': 'Busy Time',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        # Add the event
        self.storage.add_event(event_data, 'test_user')
        
        # Check times that should be unavailable (during the event)
        during_event = start_time + datetime.timedelta(minutes=30)
        self.assertFalse(self.storage.is_time_available('test_user', during_event.isoformat()))
        
        # Check time that overlaps with start
        overlap_start = start_time - datetime.timedelta(minutes=30)
        self.assertFalse(self.storage.is_time_available('test_user', overlap_start.isoformat(), 60))
        
        # Check time that overlaps with end
        overlap_end = end_time - datetime.timedelta(minutes=30)
        self.assertFalse(self.storage.is_time_available('test_user', overlap_end.isoformat(), 60))
        
        # Check times that should be available (before/after the event)
        before_event = start_time - datetime.timedelta(hours=3)
        self.assertTrue(self.storage.is_time_available('test_user', before_event.isoformat()))
        
        after_event = end_time + datetime.timedelta(hours=1)
        self.assertTrue(self.storage.is_time_available('test_user', after_event.isoformat()))


class TestCalendarManager(unittest.TestCase):
    """Test the CalendarManager class"""
    
    def setUp(self):
        """Set up a temporary database and calendar manager for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.storage = CalendarStorage(self.temp_db.name)
        self.manager = CalendarManager(self.storage)
    
    def tearDown(self):
        """Clean up the temporary database after each test"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_create_event(self):
        """Test creating an event through the manager"""
        # Create a test event
        now = datetime.datetime.now()
        
        event_id = self.manager.create_event(
            'test_user',
            'Manager Test Event',
            now.isoformat(),
            description='Testing the manager',
            location='Test Location'
        )
        
        # Check that the event was created successfully
        self.assertIsNotNone(event_id)
        
        # Get the event
        event = self.manager.get_event('test_user', event_id)
        
        # Check event details
        self.assertEqual(event['title'], 'Manager Test Event')
        self.assertEqual(event['description'], 'Testing the manager')
        self.assertEqual(event['location'], 'Test Location')
    
    def test_all_day_event(self):
        """Test creating an all-day event"""
        # Create an all-day event
        today = datetime.datetime.now().date()
        
        event_id = self.manager.create_event(
            'test_user',
            'All Day Event',
            today.isoformat(),
            all_day=True
        )
        
        # Check that the event was created successfully
        self.assertIsNotNone(event_id)
        
        # Get the event
        event = self.manager.get_event('test_user', event_id)
        
        # Check event details
        self.assertEqual(event['title'], 'All Day Event')
        self.assertTrue(event['all_day'])
    
    def test_get_events_by_date(self):
        """Test getting events for a specific date"""
        # Create events on different dates
        today = datetime.datetime.now().date()
        tomorrow = today + datetime.timedelta(days=1)
        
        # Today's event
        self.manager.create_event(
            'test_user',
            'Today Event',
            datetime.datetime.combine(today, datetime.time(14, 0)).isoformat()
        )
        
        # Tomorrow's event
        self.manager.create_event(
            'test_user',
            'Tomorrow Event',
            datetime.datetime.combine(tomorrow, datetime.time(10, 0)).isoformat()
        )
        
        # Get today's events
        today_events = self.manager.get_events_by_date('test_user', today)
        
        # Check that only today's event is included
        self.assertEqual(len(today_events), 1)
        self.assertEqual(today_events[0]['title'], 'Today Event')
        
        # Get tomorrow's events
        tomorrow_events = self.manager.get_events_by_date('test_user', tomorrow)
        
        # Check that only tomorrow's event is included
        self.assertEqual(len(tomorrow_events), 1)
        self.assertEqual(tomorrow_events[0]['title'], 'Tomorrow Event')
    
    def test_get_schedule_density(self):
        """Test calculating schedule density"""
        # Create a series of events to test density calculation
        now = datetime.datetime.now()
        
        # No events initially
        empty_density = self.manager.get_schedule_density('test_user')
        
        # Should be very low density with no events
        self.assertLess(empty_density, 0.2)
        
        # Add several events
        for i in range(5):
            self.manager.create_event(
                'test_user',
                f'Test Event {i}',
                (now + datetime.timedelta(days=i)).isoformat(),
                end_time=(now + datetime.timedelta(days=i, hours=2)).isoformat()
            )
        
        # Check density with several events
        medium_density = self.manager.get_schedule_density('test_user')
        
        # Should be medium density with several short events
        self.assertGreater(medium_density, 0.2)
        self.assertLess(medium_density, 0.8)
        
        # Add several more long events
        for i in range(5, 10):
            self.manager.create_event(
                'test_user',
                f'Long Event {i}',
                (now + datetime.timedelta(days=i//2)).isoformat(),
                end_time=(now + datetime.timedelta(days=i//2, hours=8)).isoformat()
            )
        
        # Check density with many events including long ones
        high_density = self.manager.get_schedule_density('test_user')
        
        # Should be high density with many events including long ones
        self.assertGreater(high_density, medium_density)


class TestCalendarCommands(unittest.TestCase):
    """Test the CalendarCommands class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a calendar manager with a test database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.storage = CalendarStorage(self.temp_db.name)
        self.manager = CalendarManager(self.storage)
        
        # Create a commands handler
        self.commands = CalendarCommands(self.manager)
        
        # Test user ID
        self.user_id = 'test_user'
    
    def tearDown(self):
        """Clean up after each test"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_help_command(self):
        """Test the help command"""
        response = self.commands.process_command(self.user_id, 'help')
        
        # Check that the help text was returned
        self.assertIn('Calendar Commands', response)
        self.assertIn('Add Events', response)
        self.assertIn('Show Events', response)
    
    def test_add_event_command(self):
        """Test adding an event via command"""
        # Get tomorrow's date string
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Add an event
        response = self.commands.process_command(
            self.user_id, 
            f'add Team Meeting on {tomorrow} at 2:00 PM at Conference Room'
        )
        
        # Check that the event was added successfully
        self.assertIn('Added event', response)
        self.assertIn('Team Meeting', response)
        
        # Verify that the event exists in the database
        events = self.manager.get_events_by_date(
            self.user_id, 
            (datetime.datetime.now() + datetime.timedelta(days=1)).date()
        )
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['title'], 'Team Meeting')
        self.assertEqual(events[0]['location'], 'Conference Room')
    
    def test_show_events_command(self):
        """Test showing events via command"""
        # Add some test events
        today = datetime.datetime.now()
        tomorrow = today + datetime.timedelta(days=1)
        
        self.manager.create_event(
            self.user_id,
            'Morning Meeting',
            today.replace(hour=9, minute=0).isoformat(),
            end_time=today.replace(hour=10, minute=0).isoformat()
        )
        
        self.manager.create_event(
            self.user_id,
            'Lunch Appointment',
            today.replace(hour=12, minute=0).isoformat(),
            end_time=today.replace(hour=13, minute=0).isoformat(),
            location='Cafe'
        )
        
        self.manager.create_event(
            self.user_id,
            'Tomorrow Event',
            tomorrow.replace(hour=15, minute=0).isoformat()
        )
        
        # Show today's events
        response = self.commands.process_command(self.user_id, 'show events for today')
        
        # Check that today's events are shown
        self.assertIn('Morning Meeting', response)
        self.assertIn('Lunch Appointment', response)
        self.assertIn('Cafe', response)
        self.assertNotIn('Tomorrow Event', response)
        
        # Show all events
        response = self.commands.process_command(self.user_id, 'show events')
        
        # Check that all events are shown
        self.assertIn('Morning Meeting', response)
        self.assertIn('Lunch Appointment', response)
        self.assertIn('Tomorrow Event', response)


class TestPromptEnhancer(unittest.TestCase):
    """Test the Calendar PromptEnhancer"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a pre-populated test calendar database
        self.db_path = create_test_calendar_db()
        
        # Create enhancer with the test database
        self.storage = CalendarStorage(self.db_path)
        self.manager = CalendarManager(self.storage)
        self.enhancer = PromptEnhancer(self.manager)
        
        # Test user ID
        self.user_id = 'TestUser'
        
        # Sample system prompt
        self.system_prompt = """
        I am Jupiter, an AI assistant.
        
        # Personality
        I'm helpful, knowledgeable, and friendly.
        """
    
    def tearDown(self):
        """Clean up after each test"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_enhance_prompt_with_events(self):
        """Test enhancing a prompt with calendar events"""
        enhanced_prompt = self.enhancer.enhance_prompt(self.user_id, self.system_prompt)
        
        # Check that calendar information was added
        self.assertIn('Calendar Information', enhanced_prompt)
        self.assertIn('Upcoming Events', enhanced_prompt)
        self.assertIn('Team Meeting', enhanced_prompt)
        self.assertIn('Company Workshop', enhanced_prompt)
    
    def test_enhance_prompt_detail_levels(self):
        """Test different detail levels for prompt enhancement"""
        # Minimal detail level
        minimal_prompt = self.enhancer.enhance_prompt(self.user_id, self.system_prompt, 'minimal')
        
        # Should only include today's events and be shorter
        self.assertIn('Calendar Information', minimal_prompt)
        self.assertIn('Team Meeting', minimal_prompt)
        self.assertNotIn('Project Review', minimal_prompt)  # Next week event should not be included
        
        # Detailed level
        detailed_prompt = self.enhancer.enhance_prompt(self.user_id, self.system_prompt, 'detailed')
        
        # Should include more events and possibly more information about each
        self.assertIn('Calendar Information', detailed_prompt)
        self.assertIn('Team Meeting', detailed_prompt)
        self.assertIn('Company Workshop', detailed_prompt)
        self.assertIn('Project Review', detailed_prompt)  # Next week event should be included
    
    def test_enhance_prompt_with_no_events(self):
        """Test enhancing a prompt for a user with no events"""
        # Non-existent user or user with no events
        no_events_prompt = self.enhancer.enhance_prompt('NoEventsUser', self.system_prompt)
        
        # Should indicate an open schedule
        self.assertIn('Calendar Information', no_events_prompt)
        self.assertIn('open schedule', no_events_prompt.lower())


if __name__ == '__main__':
    unittest.main()
